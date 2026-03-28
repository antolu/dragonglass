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
        let _ = menuBarManager.setup( // swiftlint:disable:this redundant_discardable_let
            backend: backend,
            client: client,
            sttManager: sttManager,
            hotkeyManager: hotkeyManager
        )
        let _ = { appDelegate.backend = backend }() // swiftlint:disable:this redundant_discardable_let

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
