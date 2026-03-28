import AppKit
import SwiftUI

@main
struct DragonglassApp: App {
    @StateObject private var backend = BackendManager()
    @StateObject private var client = AgentClient()
    @StateObject private var menuBarManager = MenuBarManager()
    @StateObject private var sttManager = STTManager()
    @StateObject private var hotkeyManager = HotkeyManager()

    var body: some Scene {
        let _ = menuBarManager.setup(
            backend: backend,
            client: client,
            sttManager: sttManager,
            hotkeyManager: hotkeyManager
        )

        Settings {
            SettingsView(isPresented: .constant(false))
                .environmentObject(backend)
                .environmentObject(client)
                .environmentObject(sttManager)
                .environmentObject(hotkeyManager)
        }
    }
}
