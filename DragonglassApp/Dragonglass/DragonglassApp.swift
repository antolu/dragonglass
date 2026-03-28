import AppKit
import SwiftUI

@main
struct DragonglassApp: App {
    @StateObject private var backend = BackendManager()
    @StateObject private var client = AgentClient()
    @StateObject private var menuBarManager = MenuBarManager()
    @StateObject private var sttManager = STTManager()
    @StateObject private var hotkeyManager = HotkeyManager()
    @NSApplicationDelegateAdaptor private var appDelegate: AppDelegate

    var body: some Scene {
        _ = menuBarManager.setup(
            backend: backend,
            client: client,
            sttManager: sttManager,
            hotkeyManager: hotkeyManager
        )
        _ = appDelegate.backend = backend

        Settings {
            SettingsView(isPresented: .constant(false))
                .environmentObject(backend)
                .environmentObject(client)
                .environmentObject(sttManager)
                .environmentObject(hotkeyManager)
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var backend: BackendManager?

    func applicationWillTerminate(_ notification: Notification) {
        backend?.cancelObsidianPoll()
    }
}
