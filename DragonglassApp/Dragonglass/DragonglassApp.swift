import SwiftUI
import AppKit

@main
struct DragonglassApp: App {
    @StateObject private var backend = BackendManager()
    @StateObject private var client = AgentClient()
    @StateObject private var menuBarManager = MenuBarManager()
    @State private var showingSettings = false

    var body: some Scene {
        Settings {
            SettingsView(isPresented: $showingSettings)
                .environmentObject(backend)
                .environmentObject(client)
                .onAppear {
                    menuBarManager.setup(backend: backend, client: client)
                }
        }
    }
}
