use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager,
};

#[tauri::command]
fn get_api_url() -> String {
    // Default: local server. Override with MAILAPP_API_URL env var.
    // Set MAILAPP_API_URL=https://op13.scigroup.fr for production HTTPS
    std::env::var("MAILAPP_API_URL")
        .unwrap_or_else(|_| "http://192.168.1.242:6000".to_string())
}

#[tauri::command]
fn set_dock_badge(_app: tauri::AppHandle, _count: u32) {
    // Dock badge: macOS-specific, implemented via tauri-plugin in future version
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // --- Menu bar ---
            let edit_menu = MenuBuilder::new(app)
                .items(&[
                    &MenuItemBuilder::with_id("cut", "Couper")
                        .accelerator("CmdOrCtrl+X")
                        .build(app)?,
                    &MenuItemBuilder::with_id("copy", "Copier")
                        .accelerator("CmdOrCtrl+C")
                        .build(app)?,
                    &MenuItemBuilder::with_id("paste", "Coller")
                        .accelerator("CmdOrCtrl+V")
                        .build(app)?,
                ])
                .build()?;

            // --- System tray ---
            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("MailApp")
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        if let Some(window) = tray.app_handle().get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            // Add edit menu to all windows
            for window in app.webview_windows().values() {
                let _ = window.clone().set_menu(edit_menu.clone());
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_api_url, set_dock_badge])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
