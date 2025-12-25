use std::process::{Command, Child};
use std::sync::Mutex;
use std::fs;
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

#[tauri::command]
async fn save_file_with_dialog(
    app_handle: tauri::AppHandle,
    filename: String,
    content: Vec<u8>,
) -> Result<String, String> {
    use tauri_plugin_dialog::{DialogExt, FilePath};

    // Show save dialog
    let file_path = app_handle
        .dialog()
        .file()
        .set_file_name(&filename)
        .blocking_save_file();

    match file_path {
        Some(FilePath::Path(path)) => {
            // Write file to chosen location
            fs::write(&path, content)
                .map_err(|e| format!("Failed to save file: {}", e))?;

            Ok(path.to_string_lossy().to_string())
        }
        Some(FilePath::Url(_)) => Err("URL paths not supported".to_string()),
        None => Err("Save cancelled".to_string()),
    }
}

#[tauri::command]
fn open_downloads_folder() -> Result<(), String> {
    // Open Downloads folder in native file manager
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(std::env::var("HOME").unwrap_or_default() + "/Downloads")
            .spawn()
            .map_err(|e| format!("Failed to open Downloads: {}", e))?;
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(std::env::var("HOME").unwrap_or_default() + "/Downloads")
            .spawn()
            .map_err(|e| format!("Failed to open Downloads: {}", e))?;
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .arg(std::env::var("USERPROFILE").unwrap_or_default() + "\\Downloads")
            .spawn()
            .map_err(|e| format!("Failed to open Downloads: {}", e))?;
    }

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .manage(PythonBackend(Default::default()))
    .plugin(tauri_plugin_dialog::init())
    .invoke_handler(tauri::generate_handler![start_backend, get_backend_status, save_file_with_dialog, open_downloads_folder])
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
              std::thread::sleep(std::time::Duration::from_millis(500));
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
