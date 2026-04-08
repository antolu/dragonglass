import AppKit
import OSLog
import SwiftUI
import UserNotifications

private let logger = Logger(subsystem: "com.lua.Dragonglass", category: "AppDelegate")

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

    func applicationDidFinishLaunching(_ notification: Notification) {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert]) { granted, error in
            if let error {
                logger.error("notification authorization failed error=\(error.localizedDescription, privacy: .public)")
            } else {
                logger.info("notification authorization granted=\(granted)")
            }
        }
        // remapDictationKeyToF13() — on ice until intelligenceplatformd interception is resolved
    }

    func applicationWillTerminate(_ notification: Notification) {
        backend?.cancelObsidianPoll()
    }
}
