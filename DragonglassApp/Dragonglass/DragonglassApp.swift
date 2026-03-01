//
//  DragonglassApp.swift
//  Dragonglass
//
//  Created by Anton Lu on 2026-02-27.
//

import SwiftUI
import AppKit

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
            Group {
                if NSImage(named: NSImage.Name("MenuBarIcon")) != nil {
                    Label("Dragonglass", image: "MenuBarIcon")
                } else {
                    Label("Dragonglass", systemImage: "sparkles")
                }
            }
            .labelStyle(.iconOnly)
                .opacity(client.isThinking ? 0.5 : 1.0)
        }
        .menuBarExtraStyle(.window)
    }
}
