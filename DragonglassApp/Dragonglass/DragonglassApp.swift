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
        MenuBarExtra {
            ContentView()
                .environmentObject(backend)
                .environmentObject(client)
        } label: {
            if #available(macOS 14.0, *) {
                Image(systemName: "sparkles")
                    .symbolEffect(.pulse, isActive: client.isThinking)
            } else {
                Image(systemName: "sparkles")
                    .opacity(client.isThinking ? 0.5 : 1.0)
            }
        }
        .menuBarExtraStyle(.window)
    }
}
