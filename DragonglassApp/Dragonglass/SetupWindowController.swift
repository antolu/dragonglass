import AppKit
import SwiftUI

@MainActor
final class SetupWindowController: NSObject, NSWindowDelegate {
    static let shared = SetupWindowController()

    private var window: NSWindow?
    private var onComplete: ((String) -> Void)?

    func show(onComplete: ((String) -> Void)? = nil) {
        self.onComplete = onComplete

        if let window {
            NSApp.activate(ignoringOtherApps: true)
            window.orderFrontRegardless()
            window.makeKeyAndOrderFront(nil)
            return
        }

        let isPresented = Binding<Bool>(
            get: { self.window != nil },
            set: { visible in
                if !visible {
                    self.closeWindow()
                }
            }
        )

        let rootView = ObsidianSetupView(
            isPresented: isPresented,
            onComplete: { [weak self] vaultPath in
                self?.onComplete?(vaultPath)
            }
        )
        let host = NSHostingController(rootView: rootView)
        let setupWindow = NSWindow(contentViewController: host)
        setupWindow.title = "Obsidian Setup"
        setupWindow.styleMask = [.titled, .closable]
        setupWindow.level = .floating
        setupWindow.collectionBehavior = [.moveToActiveSpace, .fullScreenAuxiliary]
        setupWindow.isReleasedWhenClosed = false
        setupWindow.delegate = self
        setupWindow.center()

        window = setupWindow

        NSApp.activate(ignoringOtherApps: true)
        setupWindow.orderFrontRegardless()
        setupWindow.makeKeyAndOrderFront(nil)
    }

    func windowWillClose(_ notification: Notification) {
        if let closedWindow = notification.object as? NSWindow, closedWindow == window {
            window = nil
            onComplete = nil
        }
    }

    private func closeWindow() {
        guard let window else { return }
        self.window = nil
        window.close()
    }
}
