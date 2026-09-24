use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    net::{SocketAddr, TcpStream},
    path::PathBuf,
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
    Manager, RunEvent, WindowEvent,
};
use tauri_plugin_autostart::ManagerExt as AutostartExt;
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};
use url::Url;

const READY_PREFIX: &str = "CODEX_QUOTA_DESKTOP_PORT=";
const DATA_DIRECTORY_NAME: &str = "Codex Quota Monitor";
const LOG_ROTATE_BYTES: u64 = 1_000_000;

struct BackendChild(Mutex<Option<CommandChild>>);
struct QuitState(AtomicBool);
struct DesktopLog(Mutex<Option<File>>);

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

impl DesktopLog {
    fn open() -> Self {
        let log_dir = desktop_data_dir().join("logs");
        let _ = fs::create_dir_all(&log_dir);
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
        Self(Mutex::new(
            OpenOptions::new()
                .create(true)
                .append(true)
                .open(log_path)
                .ok(),
        ))
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
        let script = format!("document.querySelector('h1').textContent = 'Codex Quota Monitor needs attention'; document.getElementById('error').textContent = {message};");
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
    let menu = Menu::with_items(app, &[&open, &autostart, &quit])?;
    TrayIconBuilder::with_id("main-tray")
        .icon(
            app.default_window_icon()
                .expect("application icon missing")
                .clone(),
        )
        .tooltip("Codex Quota Monitor - monitoring")
        .menu(&menu)
        .on_menu_event(|app, event| match event.id().as_ref() {
            "open" => show_main_window(app),
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
    Ok(())
}

fn main() {
    let app = tauri::Builder::default()
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
        .manage(DesktopLog::open())
        .setup(|app| {
            setup_tray(app.handle())?;
            if let Err(error) = start_backend(app.handle().clone()) {
                show_startup_error(app.handle(), &error);
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Codex Quota Monitor desktop shell");
    app.run(|app_handle, event| match event {
        RunEvent::WindowEvent {
            event: WindowEvent::CloseRequested { api, .. },
            ..
        } if !app_handle.state::<QuitState>().0.load(Ordering::SeqCst) => {
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
