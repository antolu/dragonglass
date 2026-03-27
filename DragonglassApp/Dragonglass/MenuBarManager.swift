import SwiftUI
import AppKit
import Combine

@MainActor
class MenuBarManager: NSObject, ObservableObject {
    private var statusItem: NSStatusItem?
    private var backend: BackendManager?
    private var client: AgentClient?
    private var popover: NSPopover?
    private var cancellables = Set<AnyCancellable>()

    func setup(backend: BackendManager, client: AgentClient) {
        guard self.backend == nil else { return }
        self.backend = backend
        self.client = client

        backend.$phase
            .receive(on: RunLoop.main)
            .sink { [weak self] _ in self?.refresh() }
            .store(in: &cancellables)

        client.$isThinking
            .receive(on: RunLoop.main)
            .sink { [weak self] _ in self?.updateIcon() }
            .store(in: &cancellables)

        refresh()
    }

    func refresh() {
        guard let backend = backend, let client = client else { return }

        let isReady: Bool
        switch backend.phase {
        case .ready, .needsPluginReload:
            isReady = true
        default:
            isReady = false
        }

        if isReady {
            if statusItem == nil {
                statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
                if let button = statusItem?.button {
                    button.action = #selector(togglePopover)
                    button.target = self
                }
                updateIcon()

                let hostingController = NSHostingController(rootView:
                    ContentView()
                        .environmentObject(backend)
                        .environmentObject(client)
                        .frame(width: 400, height: 500)
                )
                hostingController.safeAreaRegions = []
                let p = NSPopover()
                p.contentViewController = hostingController
                p.behavior = .transient
                self.popover = p
            }
        } else {
            statusItem = nil
            popover = nil
        }
    }

    private func updateIcon() {
        guard let button = statusItem?.button else { return }
        let isThinking = client?.isThinking ?? false

        if let icon = NSImage(named: "MenuBarIcon") {
            button.image = icon
        } else {
            button.image = NSImage(systemSymbolName: "sparkles", accessibilityDescription: "Dragonglass")
        }
        button.alphaValue = isThinking ? 0.5 : 1.0
    }

    @objc func togglePopover(_ sender: AnyObject?) {
        guard let button = statusItem?.button, let popover = popover else { return }
        if popover.isShown {
            popover.performClose(sender)
        } else {
            let closeOnFocusLoss = UserDefaults.standard.bool(forKey: "closePopoverOnFocusLoss")
            popover.behavior = closeOnFocusLoss ? .semitransient : .transient
            NSApplication.shared.activate(ignoringOtherApps: true)
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            popover.contentViewController?.view.window?.makeKey()
        }
    }
}
