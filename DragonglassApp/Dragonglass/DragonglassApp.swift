import SwiftUI
import AppKit

@main
struct DragonglassApp: App {
    @StateObject private var backend = BackendManager()
    @StateObject private var client = AgentClient()
    @StateObject private var menuBarManager = MenuBarManager()

    var body: some Scene {
        let _ = menuBarManager.setup(backend: backend, client: client)

        Settings {
            SettingsView(isPresented: .constant(false))
                .environmentObject(backend)
                .environmentObject(client)
        }
    }
}
