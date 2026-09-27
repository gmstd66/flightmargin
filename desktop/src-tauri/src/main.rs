#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    net::{SocketAddr, TcpStream},
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicBool, Ordering},
        Mutex,
    },
    thread,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

use tauri::{
    menu::{CheckMenuItem, Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    LogicalSize, Manager, PhysicalPosition, RunEvent, WebviewUrl, WebviewWindow,
    WebviewWindowBuilder, WindowEvent,
};
use tauri_plugin_autostart::ManagerExt as AutostartExt;
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};
use url::Url;

const READY_PREFIX: &str = "CODEX_QUOTA_DESKTOP_PORT=";
const DATA_DIRECTORY_NAME: &str = "FlightMargin";
const LEGACY_DATA_DIRECTORY_NAME: &str = "Codex Quota Monitor";
const MIGRATED_USER_FILES: [&str; 2] = ["quota.db", "desktop-preferences.json"];
const LOG_ROTATE_BYTES: u64 = 1_000_000;
const WEEKLY_INDICATOR_ID: &str = "weekly-quota-indicator";
const FIVE_HOUR_INDICATOR_ID: &str = "five-hour-quota-indicator";
const CREDITS_INDICATOR_ID: &str = "credits-indicator";
const WEEKLY_MARKER: [u8; 4] = [83, 150, 246, 255];
const FIVE_HOUR_MARKER: [u8; 4] = [168, 85, 247, 255];
const CREDITS_MARKER: [u8; 4] = [52, 211, 153, 255];
const SETTINGS_WINDOW_LABEL: &str = "settings";
const SETTINGS_WINDOW_WIDTH: f64 = 420.0;
const SETTINGS_WINDOW_HEIGHT: f64 = 450.0;
const SETTINGS_WINDOW_GAP: f64 = 16.0;
const SOURCE_CODE_URL: &str = "https://github.com/gmstd66/flightmargin";
const REPORT_ISSUE_URL: &str = "https://github.com/gmstd66/flightmargin/issues";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum SettingsSection {
    Dashboard,
    About,
}

impl SettingsSection {
    fn name(self) -> &'static str {
        match self {
            Self::Dashboard => "dashboard",
            Self::About => "about",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct ScreenRect {
    x: i32,
    y: i32,
    width: u32,
    height: u32,
}

struct BackendChild(Mutex<Option<CommandChild>>);
struct QuitState(AtomicBool);
struct DesktopLog(Mutex<Option<File>>);
struct TrayState(Mutex<Option<tauri::tray::TrayIcon>>);

fn desktop_data_dir() -> PathBuf {
    #[cfg(windows)]
    {
        std::env::var_os("LOCALAPPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(std::env::temp_dir)
            .join(DATA_DIRECTORY_NAME)
    }
    #[cfg(not(windows))]
    {
        std::env::temp_dir().join(DATA_DIRECTORY_NAME)
    }
}

fn migrate_legacy_data_at(base: &Path) -> std::io::Result<bool> {
    let destination = base.join(DATA_DIRECTORY_NAME);
    let legacy = base.join(LEGACY_DATA_DIRECTORY_NAME);
    if destination.exists() || !legacy.is_dir() {
        return Ok(false);
    }
    let sources: Vec<_> = MIGRATED_USER_FILES
        .iter()
        .map(|name| (legacy.join(name), *name))
        .filter(|(path, _)| path.is_file())
        .collect();
    if sources.is_empty() {
        return Ok(false);
    }
    fs::create_dir_all(base)?;
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_nanos())
        .unwrap_or(0);
    let staging = base.join(format!(".flightmargin-migration-{}-{nonce}", std::process::id()));
    fs::create_dir(&staging)?;
    let result = (|| {
        for (source, name) in sources {
            fs::copy(source, staging.join(name))?;
        }
        match fs::rename(&staging, &destination) {
            Ok(()) => Ok(true),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => Ok(false),
            Err(error) => Err(error),
        }
    })();
    if staging.exists() {
        let _ = fs::remove_dir_all(staging);
    }
    result
}

fn migrate_legacy_desktop_data() -> std::io::Result<bool> {
    desktop_data_dir()
        .parent()
        .map(migrate_legacy_data_at)
        .unwrap_or(Ok(false))
}

impl DesktopLog {
    fn closed() -> Self {
        Self(Mutex::new(None))
    }

    fn open(&self) -> std::io::Result<()> {
        let log_dir = desktop_data_dir().join("logs");
        fs::create_dir_all(&log_dir)?;
        let log_path = log_dir.join("desktop.log");
        if log_path
            .metadata()
            .map(|metadata| metadata.len())
            .unwrap_or(0)
            >= LOG_ROTATE_BYTES
        {
            let previous = log_dir.join("desktop.1.log");
            let _ = fs::remove_file(&previous);
            let _ = fs::rename(&log_path, previous);
        }
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(log_path)?;
        *self.0.lock().expect("desktop log state lock") = Some(file);
        Ok(())
    }
}

fn log_message(app: &tauri::AppHandle, message: &str) {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0);
    eprintln!("{message}");
    if let Ok(mut file) = app.state::<DesktopLog>().0.lock() {
        if let Some(file) = file.as_mut() {
            let _ = writeln!(file, "{timestamp} {message}");
        }
    }
}

fn show_startup_error(app: &tauri::AppHandle, error: &str) {
    log_message(app, error);
    if let Some(window) = app.get_webview_window("main") {
        let message = format!("{error:?}");
        let script = format!("document.querySelector('h1').textContent = 'FlightMargin needs attention'; document.getElementById('error').textContent = {message};");
        let _ = window.eval(script);
    }
}

fn show_main_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

fn clamp_coordinate(value: i64, minimum: i64, maximum: i64) -> i32 {
    if maximum < minimum {
        minimum as i32
    } else {
        value.clamp(minimum, maximum) as i32
    }
}

fn adjacent_window_position(
    main: ScreenRect,
    settings: ScreenRect,
    work_area: ScreenRect,
    gap: u32,
) -> (i32, i32) {
    let work_left = i64::from(work_area.x);
    let work_top = i64::from(work_area.y);
    let work_right = work_left + i64::from(work_area.width);
    let work_bottom = work_top + i64::from(work_area.height);
    let settings_width = i64::from(settings.width);
    let settings_height = i64::from(settings.height);
    let gap = i64::from(gap);

    let right_x = i64::from(main.x) + i64::from(main.width) + gap;
    let left_x = i64::from(main.x) - settings_width - gap;
    let right_fits = right_x + settings_width <= work_right;
    let left_fits = left_x >= work_left;
    let maximum_x = work_right - settings_width;
    let x = if right_fits {
        right_x as i32
    } else if left_fits {
        left_x as i32
    } else {
        clamp_coordinate(right_x, work_left, maximum_x)
    };
    let y = clamp_coordinate(
        i64::from(main.y),
        work_top,
        work_bottom - settings_height,
    );
    (x, y)
}

fn position_settings_window(
    app: &tauri::AppHandle,
    settings: &WebviewWindow,
) -> Result<(), String> {
    let main = app
        .get_webview_window("main")
        .ok_or_else(|| "Main desktop window is unavailable".to_string())?;
    let main_position = main.outer_position().map_err(|error| error.to_string())?;
    let main_size = main.outer_size().map_err(|error| error.to_string())?;
    let settings_size = settings.outer_size().map_err(|error| error.to_string())?;
    let monitor = main
        .current_monitor()
        .map_err(|error| error.to_string())?
        .or(app.primary_monitor().map_err(|error| error.to_string())?)
        .ok_or_else(|| "No Windows monitor is available".to_string())?;
    let work_area = monitor.work_area();
    let gap = (SETTINGS_WINDOW_GAP * monitor.scale_factor()).round() as u32;
    let (x, y) = adjacent_window_position(
        ScreenRect {
            x: main_position.x,
            y: main_position.y,
            width: main_size.width,
            height: main_size.height,
        },
        ScreenRect {
            x: 0,
            y: 0,
            width: settings_size.width,
            height: settings_size.height,
        },
        ScreenRect {
            x: work_area.position.x,
            y: work_area.position.y,
            width: work_area.size.width,
            height: work_area.size.height,
        },
        gap,
    );
    settings
        .set_position(PhysicalPosition::new(x, y))
        .map_err(|error| error.to_string())
}

fn open_settings_window(
    app: &tauri::AppHandle,
    section: SettingsSection,
) -> Result<(), String> {
    if let Some(settings) = app.get_webview_window(SETTINGS_WINDOW_LABEL) {
        position_settings_window(app, &settings)?;
        settings
            .eval(&format!(
                "window.openSettingsSection?.({:?});",
                section.name(),
            ))
            .map_err(|error| error.to_string())?;
        settings.show().map_err(|error| error.to_string())?;
        settings.unminimize().map_err(|error| error.to_string())?;
        settings.set_focus().map_err(|error| error.to_string())?;
        return Ok(());
    }

    let main = app
        .get_webview_window("main")
        .ok_or_else(|| "Main desktop window is unavailable".to_string())?;
    let mut url = main.url().map_err(|error| error.to_string())?;
    url.set_path("/settings");
    url.set_query(Some(&format!("section={}", section.name())));
    let settings = WebviewWindowBuilder::new(
        app,
        SETTINGS_WINDOW_LABEL,
        WebviewUrl::External(url),
    )
    .title("FlightMargin Settings")
    .inner_size(SETTINGS_WINDOW_WIDTH, SETTINGS_WINDOW_HEIGHT)
    .min_inner_size(360.0, 360.0)
    .visible(false)
    .build()
    .map_err(|error| error.to_string())?;
    position_settings_window(app, &settings)?;
    settings.show().map_err(|error| error.to_string())?;
    settings.set_focus().map_err(|error| error.to_string())
}

#[tauri::command]
async fn open_settings(app: tauri::AppHandle) -> Result<(), String> {
    open_settings_window(&app, SettingsSection::Dashboard)
}

#[tauri::command]
fn close_settings(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(settings) = app.get_webview_window(SETTINGS_WINDOW_LABEL) {
        settings.close().map_err(|error| error.to_string())?;
    }
    Ok(())
}

fn project_url(destination: &str) -> Option<&'static str> {
    match destination {
        "source" => Some(SOURCE_CODE_URL),
        "issues" => Some(REPORT_ISSUE_URL),
        _ => None,
    }
}

#[tauri::command]
fn open_project_link(app: tauri::AppHandle, destination: String) -> Result<(), String> {
    let url = project_url(&destination)
        .ok_or_else(|| "Project link is not allowed".to_string())?;
    #[allow(deprecated)]
    app.shell()
        .open(url, None)
        .map_err(|error| format!("Unable to open project link: {error}"))
}

fn tray_indicator_enabled() -> bool {
    let path = desktop_data_dir().join("desktop-preferences.json");
    let contents = fs::read_to_string(path).ok();
    tray_indicator_preference(contents.as_deref())
}

fn tray_indicator_preference(contents: Option<&str>) -> bool {
    contents
        .and_then(|text| serde_json::from_str::<serde_json::Value>(text).ok())
        .and_then(|value| value.get("tray_indicator").and_then(|enabled| enabled.as_bool()))
        .unwrap_or(true)
}

fn update_tray_quota(app: &tauri::AppHandle, five: &str, weekly: &str, credits: &str) {
    let tooltip = if tray_indicator_enabled() {
        format!("FlightMargin\nWeekly remaining: {weekly}\n5-hour remaining: {five}")
    } else {
        "FlightMargin - monitoring".to_string()
    };
    if let Ok(state) = app.state::<TrayState>().0.lock() {
        if let Some(tray) = state.as_ref() { let _ = tray.set_tooltip(Some(&tooltip)); }
    }
    sync_quota_indicators(app, five, weekly, credits);
}

fn quota_color(value: Option<u8>) -> [u8; 4] {
    match value {
        Some(value) if value <= 10 => [235, 75, 75, 255],
        Some(value) if value <= 25 => [246, 196, 83, 255],
        Some(_) => [225, 229, 235, 255],
        None => [125, 130, 139, 255],
    }
}

fn fill(pixels: &mut [u8], x: usize, y: usize, width: usize, height: usize, color: [u8; 4]) {
    for row in y..(y + height).min(32) { for column in x..(x + width).min(32) {
        let index = (row * 32 + column) * 4; pixels[index..index + 4].copy_from_slice(&color);
    }}
}

fn digit_layout(character_count: usize) -> (usize, usize, usize, usize) {
    match character_count {
        0 | 1 => (10, 0, 8, 10),
        2 => (3, 14, 8, 10),
        3 => (1, 10, 4, 6),
        _ => (1, 7, 2, 4),
    }
}

fn numeric_icon_pixels(text: &str, marker: [u8; 4], color: [u8; 4]) -> Vec<u8> {
    let mut pixels = vec![0; 32 * 32 * 4];
    fill(&mut pixels, 0, 0, 32, 4, marker);
    let segments = [[1,1,1,1,1,1,0],[0,1,1,0,0,0,0],[1,1,0,1,1,0,1],[1,1,1,1,0,0,1],[0,1,1,0,0,1,1],[1,0,1,1,0,1,1],[1,0,1,1,1,1,1],[1,1,1,0,0,0,0],[1,1,1,1,1,1,1],[1,1,1,1,0,1,1]];
    let (start, step, horizontal_width, right_offset) = digit_layout(text.len());
    for (position, character) in text.chars().enumerate() {
        if let Some(digit) = character.to_digit(10) { let x = start + position * step; let s = segments[digit as usize];
            if s[0] == 1 { fill(&mut pixels,x+2,7,horizontal_width,2,color) } if s[1] == 1 { fill(&mut pixels,x+right_offset,9,2,8,color) }
            if s[2] == 1 { fill(&mut pixels,x+right_offset,18,2,8,color) } if s[3] == 1 { fill(&mut pixels,x+2,26,horizontal_width,2,color) }
            if s[4] == 1 { fill(&mut pixels,x,18,2,8,color) } if s[5] == 1 { fill(&mut pixels,x,9,2,8,color) }
            if s[6] == 1 { fill(&mut pixels,x+2,17,horizontal_width,2,color) }
        } else if character == '+' {
            let x = start + position * step;
            fill(&mut pixels, x, 17, right_offset + 2, 2, color);
            fill(&mut pixels, x + (right_offset / 2), 12, 2, 12, color);
        } else {
            let x = start + position * step;
            fill(&mut pixels, x, 17, right_offset + 2, 2, color);
        }
    }
    pixels
}

fn quota_icon(value: Option<u8>, marker: [u8; 4]) -> tauri::image::Image<'static> {
    let text = value.map(|number| number.to_string()).unwrap_or_else(|| "--".to_string());
    tauri::image::Image::new_owned(numeric_icon_pixels(&text, marker, quota_color(value)), 32, 32)
}

fn sync_indicator(app: &tauri::AppHandle, id: &str, value: Option<u8>, marker: [u8; 4], label: &str) -> Result<(), String> {
    let tooltip = value.map(|value| format!("{label} remaining: {value}%")).unwrap_or_else(|| format!("{label} remaining: unavailable"));
    if let Some(icon) = app.tray_by_id(id) {
        icon.set_icon(Some(quota_icon(value, marker))).map_err(|error| error.to_string())?;
        icon.set_tooltip(Some(tooltip)).map_err(|error| error.to_string())?;
        return Ok(());
    }
    TrayIconBuilder::with_id(id)
        .icon(quota_icon(value, marker))
        .tooltip(tooltip)
        .build(app)
        .map_err(|error| error.to_string())?;
    log_message(app, &format!("{label} tray indicator created"));
    Ok(())
}

fn parse_percentage(value: &str) -> Option<u8> {
    let value = value.trim_end_matches('%').parse::<f64>().ok()?;
    if !value.is_finite() || !(0.0..=100.0).contains(&value) {
        return None;
    }
    Some(value.round() as u8)
}

fn parse_credits(value: &str) -> Option<u64> {
    let value = value.parse::<f64>().ok()?;
    if !value.is_finite() || value < 0.0 {
        return None;
    }
    Some(value.trunc() as u64)
}

fn credits_display(value: Option<u64>) -> String {
    match value {
        Some(value) if value > 999 => "999+".to_string(),
        Some(value) => value.to_string(),
        None => "--".to_string(),
    }
}

fn credits_color(value: Option<u64>) -> [u8; 4] {
    match value {
        Some(0) => [235, 75, 75, 255],
        Some(_) => [225, 229, 235, 255],
        None => [125, 130, 139, 255],
    }
}

fn credits_tooltip(value: Option<u64>) -> String {
    value
        .map(|value| format!("Credits remaining: {value}"))
        .unwrap_or_else(|| "Credits remaining: unavailable".to_string())
}

fn sync_credits_indicator(app: &tauri::AppHandle, raw_value: &str) -> Result<(), String> {
    let value = parse_credits(raw_value);
    let display = credits_display(value);
    let tooltip = credits_tooltip(value);
    let icon = tauri::image::Image::new_owned(
        numeric_icon_pixels(&display, CREDITS_MARKER, credits_color(value)),
        32,
        32,
    );
    if let Some(indicator) = app.tray_by_id(CREDITS_INDICATOR_ID) {
        indicator.set_icon(Some(icon)).map_err(|error| error.to_string())?;
        indicator.set_tooltip(Some(tooltip)).map_err(|error| error.to_string())?;
        return Ok(());
    }
    TrayIconBuilder::with_id(CREDITS_INDICATOR_ID)
        .icon(icon)
        .tooltip(tooltip)
        .build(app)
        .map_err(|error| error.to_string())?;
    log_message(app, "Credits tray indicator created");
    Ok(())
}

fn sync_quota_indicators(app: &tauri::AppHandle, five: &str, weekly: &str, credits: &str) {
    if !tray_indicator_enabled() {
        let _ = app.remove_tray_by_id(WEEKLY_INDICATOR_ID);
        let _ = app.remove_tray_by_id(FIVE_HOUR_INDICATOR_ID);
        let _ = app.remove_tray_by_id(CREDITS_INDICATOR_ID);
        return;
    }
    if let Err(error) = sync_indicator(app, WEEKLY_INDICATOR_ID, parse_percentage(weekly), WEEKLY_MARKER, "Weekly") {
        log_message(app, &format!("Unable to create or update Weekly tray indicator: {error}"));
    }
    if let Err(error) = sync_indicator(app, FIVE_HOUR_INDICATOR_ID, parse_percentage(five), FIVE_HOUR_MARKER, "5-hour") {
        log_message(app, &format!("Unable to create or update 5-hour tray indicator: {error}"));
    }
    if let Err(error) = sync_credits_indicator(app, credits) {
        log_message(app, &format!("Unable to create or update Credits tray indicator: {error}"));
    }
}

fn initialize_tray_icons(app: &tauri::AppHandle) {
    match setup_tray(app) {
        Ok(()) => log_message(app, "Normal application tray icon created"),
        Err(error) => log_message(app, &format!("Unable to create normal application tray icon: {error}")),
    }
    let enabled = tray_indicator_enabled();
    log_message(app, &format!("Tray indicator preference loaded: enabled={enabled}"));
    if enabled {
        sync_quota_indicators(app, "--", "--", "--");
    } else {
        log_message(app, "Informational tray indicators are disabled by user preference");
    }
}

fn wait_for_health(port: u16) -> Result<(), String> {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let deadline = Instant::now() + Duration::from_secs(15);
    while Instant::now() < deadline {
        if let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(250)) {
            let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
            if stream
                .write_all(
                    b"GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n",
                )
                .is_ok()
            {
                let mut response = String::new();
                if stream.read_to_string(&mut response).is_ok()
                    && response.starts_with("HTTP/1.1 200")
                {
                    return Ok(());
                }
            }
        }
        thread::sleep(Duration::from_millis(150));
    }
    Err("Desktop backend did not become healthy within 15 seconds".to_string())
}

fn start_backend(app: tauri::AppHandle) -> Result<(), String> {
    let command = app
        .shell()
        .sidecar("codex-quota-backend")
        .map_err(|error| format!("Unable to resolve desktop backend: {error}"))?
        .args(["--port", "0"]);
    let (mut events, child) = command
        .spawn()
        .map_err(|error| format!("Unable to start desktop backend: {error}"))?;
    app.state::<BackendChild>()
        .0
        .lock()
        .map_err(|_| "Desktop backend state lock was poisoned".to_string())?
        .replace(child);
    log_message(
        &app,
        "Desktop backend started; waiting for loopback readiness",
    );
    let window = app
        .get_webview_window("main")
        .ok_or_else(|| "Main desktop window was not created".to_string())?;
    let error_app = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes);
                    if let Some(port_text) = line.trim().strip_prefix(READY_PREFIX) {
                        match port_text.parse::<u16>() {
                            Ok(port) if port != 0 => match wait_for_health(port) {
                                Ok(()) => {
                                    log_message(&error_app, "Desktop backend is ready on loopback");
                                    match Url::parse(&format!("http://127.0.0.1:{port}/")) {
                                        Ok(url) => { if let Err(error) = window.navigate(url) { show_startup_error(&error_app, &format!("Unable to load dashboard: {error}")); } }
                                        Err(error) => show_startup_error(&error_app, &format!("Invalid backend URL: {error}")),
                                    }
                                }
                                Err(error) => show_startup_error(&error_app, &error),
                            },
                            _ => show_startup_error(&error_app, "Desktop backend reported an invalid port"),
                        }
                    } else if let Some(values) = line.trim().strip_prefix("Quota sample: ") {
                        let parts: Vec<_> = values.split_whitespace().collect();
                        if parts.len() >= 2 {
                            let five = parts[0].strip_prefix("5h=").unwrap_or("--");
                            let weekly = parts[1].strip_prefix("weekly=").unwrap_or("--");
                            let credits = parts
                                .get(2)
                                .and_then(|value| value.strip_prefix("credits="))
                                .unwrap_or("--");
                            update_tray_quota(&error_app, five, weekly, credits);
                        }
                    }
                }
                CommandEvent::Stderr(bytes) => log_message(&error_app, &format!("Desktop backend error: {}", String::from_utf8_lossy(&bytes).trim_end())),
                CommandEvent::Error(error) => show_startup_error(&error_app, &format!("Desktop backend error: {error}")),
                CommandEvent::Terminated(payload) if !error_app.state::<QuitState>().0.load(Ordering::SeqCst) => show_startup_error(&error_app, &format!("Desktop backend stopped unexpectedly: {payload:?}. Reopen the application to restart monitoring.")),
                _ => {}
            }
        }
    });
    Ok(())
}

fn stop_backend(app: &tauri::AppHandle) {
    app.state::<QuitState>().0.store(true, Ordering::SeqCst);
    let child = app
        .state::<BackendChild>()
        .0
        .lock()
        .ok()
        .and_then(|mut state| state.take());
    if let Some(child) = child {
        #[cfg(windows)]
        {
            let result = std::process::Command::new("taskkill")
                .args(["/PID", &child.pid().to_string(), "/T", "/F"])
                .status();
            if let Err(error) = result {
                log_message(app, &format!("Unable to stop desktop backend: {error}"));
            }
        }
        #[cfg(not(windows))]
        if let Err(error) = child.kill() {
            log_message(app, &format!("Unable to stop desktop backend: {error}"));
        }
        log_message(app, "Desktop backend stopped");
    }
}

fn setup_tray(app: &tauri::AppHandle) -> tauri::Result<()> {
    let open = MenuItem::with_id(app, "open", "Open", true, None::<&str>)?;
    let settings = MenuItem::with_id(app, "settings", "Settings...", true, None::<&str>)?;
    let about = MenuItem::with_id(app, "about", "About...", true, None::<&str>)?;
    let autostart_enabled = app.autolaunch().is_enabled().unwrap_or(false);
    let autostart = CheckMenuItem::with_id(
        app,
        "autostart",
        "Start at login",
        true,
        autostart_enabled,
        None::<&str>,
    )?;
    let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&open, &settings, &about, &autostart, &quit])?;
    let tray = TrayIconBuilder::with_id("main-tray")
        .icon(
            app.default_window_icon()
                .expect("application icon missing")
                .clone(),
        )
        .tooltip("FlightMargin - monitoring")
        .menu(&menu)
        .on_menu_event(|app, event| match event.id().as_ref() {
            "open" => show_main_window(app),
            "settings" => {
                if let Err(error) = open_settings_window(app, SettingsSection::Dashboard) {
                    log_message(app, &format!("Unable to open Settings: {error}"));
                }
            }
            "about" => {
                if let Err(error) = open_settings_window(app, SettingsSection::About) {
                    log_message(app, &format!("Unable to open About: {error}"));
                }
            }
            "autostart" => {
                let result = if app.autolaunch().is_enabled().unwrap_or(false) {
                    app.autolaunch().disable()
                } else {
                    app.autolaunch().enable()
                };
                if let Err(error) = result {
                    log_message(
                        app,
                        &format!("Unable to update start-at-login setting: {error}"),
                    );
                }
            }
            "quit" => {
                stop_backend(app);
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if matches!(
                event,
                TrayIconEvent::Click {
                    button: MouseButton::Left,
                    button_state: MouseButtonState::Up,
                    ..
                }
            ) {
                show_main_window(&tray.app_handle());
            }
        })
        .build(app)?;
    *app.state::<TrayState>().0.lock().expect("tray state lock") = Some(tray);
    Ok(())
}

fn main() {
    let migration = migrate_legacy_desktop_data();
    let app = tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            open_settings,
            close_settings,
            open_project_link
        ])
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            None,
        ))
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            show_main_window(app)
        }))
        .manage(BackendChild(Mutex::new(None)))
        .manage(QuitState(AtomicBool::new(false)))
        .manage(DesktopLog::closed())
        .manage(TrayState(Mutex::new(None)))
        .setup(move |app| {
            let migrated = match &migration {
                Ok(migrated) => *migrated,
                Err(error) => {
                    show_startup_error(app.handle(), &format!("Unable to migrate legacy user data: {error}"));
                    return Ok(());
                }
            };
            if let Err(error) = app.state::<DesktopLog>().open() {
                show_startup_error(app.handle(), &format!("Unable to open FlightMargin logs: {error}"));
                return Ok(());
            }
            if migrated {
                log_message(app.handle(), "Legacy user data copied to FlightMargin");
            }
            // Existing installations may have been created before the compact
            // default. Apply it explicitly so an older native window geometry
            // cannot override the current 600x450 product default.
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_size(LogicalSize::new(600.0, 450.0));
            }
            initialize_tray_icons(app.handle());
            if let Err(error) = start_backend(app.handle().clone()) {
                show_startup_error(app.handle(), &error);
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building FlightMargin desktop shell");
    app.run(|app_handle, event| match event {
        RunEvent::WindowEvent {
            label,
            event: WindowEvent::CloseRequested { api, .. },
            ..
        } if label == "main" && !app_handle.state::<QuitState>().0.load(Ordering::SeqCst) => {
            api.prevent_close();
            if let Some(window) = app_handle.get_webview_window("main") {
                let _ = window.hide();
            }
            log_message(app_handle, "Dashboard hidden to tray");
        }
        RunEvent::ExitRequested { .. } | RunEvent::Exit => stop_backend(app_handle),
        _ => {}
    });
}

#[cfg(test)]
mod tests {
    use super::{
        adjacent_window_position, credits_color, credits_display, credits_tooltip,
        digit_layout, migrate_legacy_data_at, numeric_icon_pixels, parse_credits,
        parse_percentage, project_url, quota_color,
        tray_indicator_preference, ScreenRect, SettingsSection, CREDITS_INDICATOR_ID,
        FIVE_HOUR_INDICATOR_ID, WEEKLY_INDICATOR_ID,
    };

    #[test]
    fn legacy_data_migration_is_copy_only_and_idempotent() {
        let root = std::env::temp_dir().join(format!(
            "flightmargin-rust-migration-test-{}",
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&root);
        let legacy = root.join("Codex Quota Monitor");
        std::fs::create_dir_all(legacy.join("logs")).expect("create legacy fixture");
        std::fs::write(legacy.join("quota.db"), b"history").expect("write database fixture");
        std::fs::write(legacy.join("desktop-preferences.json"), b"preferences")
            .expect("write preferences fixture");
        std::fs::write(legacy.join("logs").join("desktop.log"), b"legacy log")
            .expect("write log fixture");

        assert!(migrate_legacy_data_at(&root).expect("first migration"));
        assert_eq!(
            std::fs::read(root.join("FlightMargin").join("quota.db")).expect("migrated database"),
            b"history"
        );
        assert!(root.join("Codex Quota Monitor").join("quota.db").is_file());
        assert!(!root.join("FlightMargin").join("logs").exists());

        std::fs::write(root.join("FlightMargin").join("quota.db"), b"new history")
            .expect("update new database");
        assert!(!migrate_legacy_data_at(&root).expect("repeat migration"));
        assert_eq!(
            std::fs::read(root.join("FlightMargin").join("quota.db")).expect("preserved database"),
            b"new history"
        );
        std::fs::remove_dir_all(root).expect("remove migration fixture");
    }

    #[test]
    fn settings_sections_route_to_one_native_settings_page() {
        assert_eq!(SettingsSection::Dashboard.name(), "dashboard");
        assert_eq!(SettingsSection::About.name(), "about");
    }

    #[test]
    fn project_links_are_exactly_allowlisted() {
        assert_eq!(
            project_url("source"),
            Some("https://github.com/gmstd66/flightmargin")
        );
        assert_eq!(
            project_url("issues"),
            Some("https://github.com/gmstd66/flightmargin/issues")
        );
        assert_eq!(project_url("https://example.com"), None);
        assert_eq!(project_url("sponsor"), None);
    }

    #[test]
    fn parses_integer_and_decimal_percentages() {
        assert_eq!(parse_percentage("0%"), Some(0));
        assert_eq!(parse_percentage("9.4%"), Some(9));
        assert_eq!(parse_percentage("10.5%"), Some(11));
        assert_eq!(parse_percentage("25.0%"), Some(25));
        assert_eq!(parse_percentage("99.6%"), Some(100));
        assert_eq!(parse_percentage("100.0%"), Some(100));
    }

    #[test]
    fn rejects_missing_invalid_and_out_of_range_percentages() {
        assert_eq!(parse_percentage("--"), None);
        assert_eq!(parse_percentage("NaN%"), None);
        assert_eq!(parse_percentage("-1%"), None);
        assert_eq!(parse_percentage("101%"), None);
    }

    #[test]
    fn tray_indicator_preference_defaults_enabled_and_respects_explicit_false() {
        assert!(tray_indicator_preference(None));
        assert!(tray_indicator_preference(Some("not json")));
        assert!(tray_indicator_preference(Some("{}")));
        assert!(tray_indicator_preference(Some(r#"{"tray_indicator": true}"#)));
        assert!(!tray_indicator_preference(Some(r#"{"tray_indicator": false}"#)));
    }

    #[test]
    fn informational_tray_ids_are_unique() {
        let ids = [
            WEEKLY_INDICATOR_ID,
            FIVE_HOUR_INDICATOR_ID,
            CREDITS_INDICATOR_ID,
        ];
        for (index, id) in ids.iter().enumerate() {
            assert!(!ids[index + 1..].contains(id), "duplicate tray id: {id}");
        }
    }

    #[test]
    fn tray_renderer_handles_required_percentage_boundaries() {
        let marker = [83, 150, 246, 255];
        for value in [0, 9, 10, 25, 99, 100] {
            let text = value.to_string();
            let pixels = numeric_icon_pixels(&text, marker, quota_color(Some(value)));
            assert_eq!(pixels.len(), 32 * 32 * 4);
            assert!(pixels.chunks_exact(4).any(|pixel| pixel == quota_color(Some(value))));
        }
    }

    #[test]
    fn tray_renderer_fits_all_three_digits_of_100_inside_the_icon() {
        let value = 100;
        let text = value.to_string();
        let (start, step, _horizontal_width, right_offset) = digit_layout(text.len());
        let digit_width = right_offset + 2;
        let pixels = numeric_icon_pixels(&text, [168, 85, 247, 255], quota_color(Some(value)));
        let color = quota_color(Some(value));

        for position in 0..text.len() {
            let left = start + position * step;
            let right = left + digit_width;
            assert!(right <= 32, "digit {position} exceeds the icon bounds");
            assert!((7..28).any(|y| {
                (left..right).any(|x| pixels[(y * 32 + x) * 4..(y * 32 + x + 1) * 4] == color)
            }), "digit {position} was not rendered");
        }
    }

    #[test]
    fn credits_are_truncated_to_whole_balances_without_rounding_up() {
        assert_eq!(parse_credits("0"), Some(0));
        assert_eq!(parse_credits("0.9"), Some(0));
        assert_eq!(parse_credits("1.9"), Some(1));
        assert_eq!(parse_credits("99.9"), Some(99));
        assert_eq!(parse_credits("100.9"), Some(100));
        assert_eq!(parse_credits("365.89305"), Some(365));
        assert_eq!(parse_credits("999.9"), Some(999));
        assert_eq!(parse_credits("--"), None);
        assert_eq!(parse_credits("NaN"), None);
    }

    #[test]
    fn credits_use_compact_overflow_and_neutral_unknown_representation() {
        assert_eq!(credits_display(Some(999)), "999");
        assert_eq!(credits_display(Some(1000)), "999+");
        assert_eq!(credits_display(None), "--");
        assert_eq!(credits_tooltip(Some(365)), "Credits remaining: 365");
        assert_eq!(credits_tooltip(Some(1000)), "Credits remaining: 1000");
        assert_eq!(credits_tooltip(None), "Credits remaining: unavailable");
        assert_eq!(credits_color(Some(0)), [235, 75, 75, 255]);
        assert_eq!(credits_color(Some(365)), [225, 229, 235, 255]);
        assert_eq!(credits_color(None), [125, 130, 139, 255]);
    }

    #[test]
    fn credits_three_digits_and_overflow_glyph_fit_inside_the_icon() {
        for text in ["100", "365", "999", "999+"] {
            let (start, step, _horizontal_width, right_offset) = digit_layout(text.len());
            let glyph_width = right_offset + 2;
            let pixels = numeric_icon_pixels(text, [52, 211, 153, 255], [225, 229, 235, 255]);
            assert_eq!(pixels.len(), 32 * 32 * 4);
            for position in 0..text.len() {
                let left = start + position * step;
                let right = left + glyph_width;
                assert!(right <= 32, "{text} glyph {position} exceeds the icon bounds");
                assert!((7..28).any(|y| {
                    (left..right).any(|x| pixels[(y * 32 + x) * 4..(y * 32 + x + 1) * 4] == [225, 229, 235, 255])
                }), "{text} glyph {position} was not rendered");
            }
        }
    }

    #[test]
    fn settings_prefers_the_right_then_the_left_of_the_main_window() {
        let work_area = ScreenRect { x: 0, y: 0, width: 1920, height: 1040 };
        let settings = ScreenRect { x: 0, y: 0, width: 420, height: 450 };
        assert_eq!(
            adjacent_window_position(
                ScreenRect { x: 200, y: 100, width: 600, height: 450 },
                settings,
                work_area,
                16,
            ),
            (816, 100)
        );
        assert_eq!(
            adjacent_window_position(
                ScreenRect { x: 1250, y: 100, width: 600, height: 450 },
                settings,
                work_area,
                16,
            ),
            (814, 100)
        );
    }

    #[test]
    fn settings_clamps_inside_the_monitor_work_area_when_neither_side_fits() {
        assert_eq!(
            adjacent_window_position(
                ScreenRect { x: 120, y: -40, width: 600, height: 450 },
                ScreenRect { x: 0, y: 0, width: 420, height: 450 },
                ScreenRect { x: 100, y: 20, width: 900, height: 700 },
                24,
            ),
            (580, 20)
        );
    }
}
