use std::{
    io::{Read, Write},
    net::{SocketAddr, TcpStream},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{process::{Child, CommandEvent}, ShellExt};
use url::Url;

const READY_PREFIX: &str = "CODEX_QUOTA_DESKTOP_PORT=";

struct BackendChild(Mutex<Option<Child>>);

fn wait_for_health(port: u16) -> Result<(), String> {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let deadline = Instant::now() + Duration::from_secs(15);

    while Instant::now() < deadline {
        if let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(250)) {
            let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
            if stream
                .write_all(b"GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
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
        .map_err(|error| format!("Unable to resolve desktop backend: {error}"))
        .args(["--port", "0"]);

    let (mut events, child) = command
        .spawn()
        .map_err(|error| format!("Unable to start desktop backend: {error}"))?;

    app.state::<BackendChild>()
        .0
        .lock()
        .map_err(|_| "Desktop backend state lock was poisoned".to_string())?
        .replace(child);

    let window = app
        .get_webview_window("main")
        .ok_or_else(|| "Main desktop window was not created".to_string())?;

    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes);
                    if let Some(port_text) = line.trim().strip_prefix(READY_PREFIX) {
                        match port_text.parse::<u16>() {
                            Ok(port) if port != 0 => {
                                if let Err(error) = wait_for_health(port) {
                                    eprintln!("{error}");
                                    continue;
                                }
                                let dashboard_url = format!("http://127.0.0.1:{port}/");
                                match Url::parse(&dashboard_url) {
                                    Ok(url) => {
                                        if let Err(error) = window.navigate(url) {
                                            eprintln!("Unable to load dashboard: {error}");
                                        }
                                    }
                                    Err(error) => eprintln!("Invalid backend URL: {error}"),
                                }
                            }
                            _ => eprintln!("Desktop backend reported an invalid port"),
                        }
                    } else {
                        println!("desktop backend: {}", line.trim_end());
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    eprintln!("desktop backend: {}", String::from_utf8_lossy(&bytes));
                }
                CommandEvent::Error(error) => eprintln!("Desktop backend error: {error}"),
                CommandEvent::Terminated(payload) => {
                    eprintln!("Desktop backend exited: {payload:?}");
                }
                _ => {}
            }
        }
    });

    Ok(())
}

fn stop_backend(app: &tauri::AppHandle) {
    let child = app
        .state::<BackendChild>()
        .0
        .lock()
        .ok()
        .and_then(|mut state| state.take());

    if let Some(child) = child {
        if let Err(error) = child.kill() {
            eprintln!("Unable to stop desktop backend: {error}");
        }
    }
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendChild(Mutex::new(None)))
        .setup(|app| start_backend(app.handle().clone()).map_err(Into::into))
        .build(tauri::generate_context!())
        .expect("error while building Codex Quota Monitor desktop shell");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
            stop_backend(app_handle);
        }
    });
}
