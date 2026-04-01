import AppKit
import Combine
import SwiftUI

@MainActor
class MenuBarManager: NSObject, ObservableObject {
    private var statusItem: NSStatusItem?
    private var backend: BackendManager?
    private var client: AgentClient?
    private var sttManager: STTManager?
    private var hotkeyManager: HotkeyManager?
    private var popover: NSPopover?
    private var cancellables = Set<AnyCancellable>()

    func setup(
        backend: BackendManager,
        client: AgentClient,
        sttManager: STTManager,
        hotkeyManager: HotkeyManager
    ) {
        guard self.backend == nil else { return }
        self.backend = backend
        self.client = client
        self.sttManager = sttManager
        self.hotkeyManager = hotkeyManager

        hotkeyManager.setup(sttManager: sttManager, menuBarManager: self, agentClient: client)

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
        guard let backend = backend, let client = client,
              let sttManager = sttManager, let hotkeyManager = hotkeyManager else { return }

        let isReady: Bool
        switch backend.phase {
        case .ready, .needsPluginReload, .needsPluginUpdate:
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
                    button.sendAction(on: .leftMouseDown)
                }
                updateIcon()

                let hostingController = NSHostingController(rootView:
                    ContentView()
                        .environmentObject(backend)
                        .environmentObject(client)
                        .environmentObject(sttManager)
                        .environmentObject(hotkeyManager)
                )
                hostingController.safeAreaRegions = []
                let p = NSPopover()
                p.contentViewController = hostingController
                p.behavior = .transient
                p.contentSize = NSSize(width: 400, height: 500)
                self.popover = p
            }
        } else {
            statusItem = nil
            popover = nil
        }
    }

    func showPopover() {
        guard let statusButton = statusItem?.button, let popover, !popover.isShown else { return }
        let closeOnFocusLoss = UserDefaults.standard.bool(forKey: "closePopoverOnFocusLoss")
        popover.behavior = closeOnFocusLoss ? .semitransient : .transient
        NSApplication.shared.activate(ignoringOtherApps: true)
        popover.show(relativeTo: statusButton.bounds, of: statusButton, preferredEdge: .minY)
        if let window = popover.contentViewController?.view.window {
            window.minSize = NSSize(width: 400, height: 500)
            window.makeKey()
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
        guard let popover else { return }
        if popover.isShown {
            popover.performClose(sender)
        } else {
            showPopover()
        }
    }
}
