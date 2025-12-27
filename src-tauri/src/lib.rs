use std::process::{Command, Child, Stdio};
use std::sync::Mutex;
use std::fs;
use std::io::{BufRead, BufReader};
use tauri::Manager;

struct PythonBackend {
    process: Mutex<Option<Child>>,
    port: Mutex<Option<u16>>,
}

#[tauri::command]
fn start_backend(app_handle: tauri::AppHandle) -> Result<String, String> {
    // In development, Python backend runs separately on port 8080
    if cfg!(debug_assertions) {
        let state: tauri::State<PythonBackend> = app_handle.state();
        *state.port.lock().unwrap() = Some(8080);
        return Ok("Development mode - Python backend should be started manually on port 8080".to_string());
    }

    // Get the sidecar path
    let sidecar_path = app_handle
        .path()
        .resource_dir()
        .map_err(|e| format!("Failed to get resource dir: {}", e))?
        .join("binaries")
        .join("cribl-hc-backend");

    // Start backend with random port (0 = auto-assign)
    let mut child = Command::new(&sidecar_path)
        .arg("--port")
        .arg("0")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}", e))?;

    // Read the port from stdout (backend will print it)
    let stdout = child.stdout.take().ok_or("Failed to capture stdout")?;
    let reader = BufReader::new(stdout);

    let mut port: Option<u16> = None;
    for line in reader.lines().take(10) {
        if let Ok(line) = line {
            // Look for line like "PORT:8080"
            if line.starts_with("PORT:") {
                if let Ok(p) = line[5..].trim().parse::<u16>() {
                    port = Some(p);
                    break;
                }
            }
        }
    }

    let port = port.ok_or("Failed to read port from backend")?;

    let state: tauri::State<PythonBackend> = app_handle.state();
    *state.process.lock().unwrap() = Some(child);
    *state.port.lock().unwrap() = Some(port);

    Ok(format!("Backend started on port {}", port))
}

#[tauri::command]
fn get_backend_url(app_handle: tauri::AppHandle) -> Result<String, String> {
    let state: tauri::State<PythonBackend> = app_handle.state();
    let port = state.port.lock().unwrap();

    match *port {
        Some(p) => Ok(format!("http://localhost:{}", p)),
        None => Err("Backend not started yet".to_string()),
    }
}

#[tauri::command]
fn get_backend_status(app_handle: tauri::AppHandle) -> Result<String, String> {
    let url = get_backend_url(app_handle)?;
    Ok(format!("Backend status: Running on {}", url))
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
    .manage(PythonBackend {
        process: Default::default(),
        port: Default::default(),
    })
    .plugin(tauri_plugin_dialog::init())
    .invoke_handler(tauri::generate_handler![start_backend, get_backend_url, get_backend_status, save_file_with_dialog, open_downloads_folder])
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
