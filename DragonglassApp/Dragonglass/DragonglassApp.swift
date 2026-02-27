//
//  DragonglassApp.swift
//  Dragonglass
//
//  Created by Anton Lu on 2026-02-27.
//

import SwiftUI

@main
struct DragonglassApp: App {
    @StateObject private var backend = BackendManager()
    @StateObject private var client = AgentClient()

    var body: some Scene {
        MenuBarExtra("Dragonglass", systemImage: "sparkles") {
            ContentView()
                .environmentObject(backend)
                .environmentObject(client)
        }
        .menuBarExtraStyle(.window)
    }
}
