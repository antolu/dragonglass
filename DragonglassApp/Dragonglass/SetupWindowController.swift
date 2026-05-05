import AppKit
import SwiftUI

@MainActor
final class SetupWindowController: NSObject, NSWindowDelegate {
    static let shared = SetupWindowController()

    private var obsidianWindow: NSWindow?
    private var pythonWindow: NSWindow?
    private var onObsidianComplete: ((String) -> Void)?
    private weak var pythonBackend: BackendManager?
    private var pythonSetupRequired = false

    func showObsidianSetup(onComplete: ((String) -> Void)? = nil) {
        self.onObsidianComplete = onComplete

        if let window = obsidianWindow {
            NSApp.activate(ignoringOtherApps: true)
            window.orderFrontRegardless()
            window.makeKeyAndOrderFront(nil)
            return
        }

        let isPresented = Binding<Bool>(
            get: { self.obsidianWindow != nil },
            set: { visible in if !visible { self.closeObsidianWindow() } }
        )

        let rootView = ObsidianSetupView(
            isPresented: isPresented,
            onComplete: { [weak self] vaultPath in self?.onObsidianComplete?(vaultPath) }
        )
        obsidianWindow = makeWindow(rootView, title: "Obsidian Setup")
    }

    func showPythonSetup(backend: BackendManager, required: Bool = false) {
        if let window = pythonWindow {
            NSApp.activate(ignoringOtherApps: true)
            window.orderFrontRegardless()
            window.makeKeyAndOrderFront(nil)
            return
        }

        let isPresented = Binding<Bool>(
            get: { self.pythonWindow != nil },
            set: { visible in if !visible { self.closePythonWindow() } }
        )

        pythonBackend = backend
        pythonSetupRequired = required
        let rootView = PythonSetupView(isPresented: isPresented)
            .environmentObject(backend)
        pythonWindow = makeWindow(rootView, title: "Dragonglass — Environment Setup")
    }

    func windowWillClose(_ notification: Notification) {
        guard let closed = notification.object as? NSWindow else { return }
        if closed == obsidianWindow {
            obsidianWindow = nil
            onObsidianComplete = nil
        } else if closed == pythonWindow {
            pythonWindow = nil
            if pythonSetupRequired, let backend = pythonBackend {
                if case .ready = backend.phase { } else {
                    NSApp.terminate(nil)
                }
            }
            pythonBackend = nil
            pythonSetupRequired = false
        }
    }

    private func makeWindow<V: View>(_ rootView: V, title: String) -> NSWindow {
        let host = NSHostingController(rootView: rootView)
        let window = NSWindow(contentViewController: host)
        window.title = title
        window.styleMask = [.titled, .closable]
        window.level = .floating
        window.collectionBehavior = [.moveToActiveSpace, .fullScreenAuxiliary]
        window.isReleasedWhenClosed = false
        window.delegate = self
        window.center()
        NSApp.activate(ignoringOtherApps: true)
        window.orderFrontRegardless()
        window.makeKeyAndOrderFront(nil)
        return window
    }

    private func closeObsidianWindow() {
        guard let window = obsidianWindow else { return }
        obsidianWindow = nil
        window.close()
    }

    private func closePythonWindow() {
        guard let window = pythonWindow else { return }
        pythonWindow = nil
        window.close()
    }
}
