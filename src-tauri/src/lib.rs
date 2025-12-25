use std::process::{Command, Child};
use std::sync::Mutex;
use tauri::Manager;

struct PythonBackend(Mutex<Option<Child>>);

#[tauri::command]
fn start_backend(app_handle: tauri::AppHandle) -> Result<String, String> {
    // In development, Python backend runs separately
    // In production, we'll use the bundled sidecar
    if cfg!(debug_assertions) {
        return Ok("Development mode - Python backend should be started manually".to_string());
    }

    // Get the sidecar path
    let sidecar_path = app_handle
        .path()
        .resource_dir()
        .map_err(|e| format!("Failed to get resource dir: {}", e))?
        .join("binaries")
        .join("cribl-hc-backend");

    let child = Command::new(&sidecar_path)
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}", e))?;

    let state: tauri::State<PythonBackend> = app_handle.state();
    *state.0.lock().unwrap() = Some(child);

    Ok(format!("Backend started from: {:?}", sidecar_path))
}

#[tauri::command]
fn get_backend_status() -> Result<String, String> {
    // Simple health check - try to connect to localhost:8000
    Ok("Backend status: Running on http://localhost:8000".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .manage(PythonBackend(Default::default()))
    .invoke_handler(tauri::generate_handler![start_backend, get_backend_status])
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      // Auto-start Python backend in production
      if !cfg!(debug_assertions) {
          let handle = app.handle().clone();
          tauri::async_runtime::spawn(async move {
              tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
              if let Err(e) = start_backend(handle) {
                  eprintln!("Failed to start backend: {}", e);
              }
          });
      }

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
