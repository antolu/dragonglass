import AppKit
import Carbon
import Combine

private final class HotkeyState: @unchecked Sendable {
    var keyCode: Int = 0
    var carbonModifiers: Int = 0
    var isPressed = false
}

@MainActor
final class HotkeyManager: NSObject, ObservableObject {
    @Published var accessibilityGranted = false

    private weak var sttManager: STTManager?
    private weak var menuBarManager: MenuBarManager?

    private var eventTap: CFMachPort?
    private var runLoopSource: CFRunLoopSource?

    nonisolated private let state = HotkeyState()

    func setup(sttManager: STTManager, menuBarManager: MenuBarManager) {
        self.sttManager = sttManager
        self.menuBarManager = menuBarManager
        refreshAccessibility()
        registerIfPossible()
    }

    func refreshAccessibility() {
        accessibilityGranted = AXIsProcessTrusted()
        sttManager?.accessibilityGranted = accessibilityGranted
    }

    func registerIfPossible() {
        unregister()
        guard AXIsProcessTrusted() else { return }
        let keyCode = UserDefaults.standard.integer(forKey: "sttHotkeyKeyCode")
        let modifiers = UserDefaults.standard.integer(forKey: "sttHotkeyModifiers")
        guard keyCode != 0 else { return }
        state.keyCode = keyCode
        state.carbonModifiers = modifiers
        installEventTap()
    }

    private func installEventTap() {
        let mask: CGEventMask =
            (1 << CGEventType.keyDown.rawValue) |
            (1 << CGEventType.keyUp.rawValue) |
            (1 << CGEventType.flagsChanged.rawValue)

        let callback: CGEventTapCallBack = { _, type, event, userInfo -> Unmanaged<CGEvent>? in
            guard let userInfo else { return Unmanaged.passUnretained(event) }
            let manager = Unmanaged<HotkeyManager>.fromOpaque(userInfo).takeUnretainedValue()
            return manager.handleEvent(type: type, event: event)
        }

        guard let tap = CGEvent.tapCreate(
            tap: .cgSessionEventTap,
            place: .headInsertEventTap,
            options: .defaultTap,
            eventsOfInterest: mask,
            callback: callback,
            userInfo: Unmanaged.passUnretained(self).toOpaque()
        ) else {
            print("[HotkeyManager] CGEvent.tapCreate failed — check Input Monitoring permission")
            return
        }

        eventTap = tap
        let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)
        runLoopSource = source
        CFRunLoopAddSource(CFRunLoopGetMain(), source, .commonModes)
        CGEvent.tapEnable(tap: tap, enable: true)
    }

    nonisolated private func handleEvent(type: CGEventType, event: CGEvent) -> Unmanaged<CGEvent>? {
        let keyCode = Int(event.getIntegerValueField(.keyboardEventKeycode))
        let cgFlags = event.flags

        let nsFlags = NSEvent.ModifierFlags(rawValue: UInt(cgFlags.rawValue))
        let eventCarbon = HotkeyManager.toCarbonModifiers(nsFlags)

        switch type {
        case .keyDown:
            guard keyCode == state.keyCode, eventCarbon == state.carbonModifiers, !state.isPressed else {
                return Unmanaged.passUnretained(event)
            }
            state.isPressed = true
            Task { @MainActor in self.onKeyDown() }
            return nil

        case .keyUp:
            guard keyCode == state.keyCode, state.isPressed else {
                return Unmanaged.passUnretained(event)
            }
            state.isPressed = false
            Task { @MainActor in self.onKeyUp() }
            return nil

        case .flagsChanged:
            guard state.isPressed else { return Unmanaged.passUnretained(event) }
            let requiredNSFlags = HotkeyManager.toNSModifiers(carbonModifiers: state.carbonModifiers)
            if !nsFlags.contains(requiredNSFlags) {
                state.isPressed = false
                Task { @MainActor in self.onKeyUp() }
            }
            return Unmanaged.passUnretained(event)

        default:
            return Unmanaged.passUnretained(event)
        }
    }

    private func unregister() {
        if let tap = eventTap {
            CGEvent.tapEnable(tap: tap, enable: false)
            if let source = runLoopSource {
                CFRunLoopRemoveSource(CFRunLoopGetMain(), source, .commonModes)
            }
            eventTap = nil
            runLoopSource = nil
        }
        state.isPressed = false
    }

    func onKeyDown() {
        sttManager?.startRecording()
    }

    func onKeyUp() {
        sttManager?.stopAndTranscribe()
        menuBarManager?.showPopover()
    }

    nonisolated static func toCarbonModifiers(_ flags: NSEvent.ModifierFlags) -> Int {
        var carbon = 0
        if flags.contains(.command) { carbon |= cmdKey }
        if flags.contains(.shift) { carbon |= shiftKey }
        if flags.contains(.option) { carbon |= optionKey }
        if flags.contains(.control) { carbon |= controlKey }
        return carbon
    }

    nonisolated static func toNSModifiers(carbonModifiers: Int) -> NSEvent.ModifierFlags {
        var flags: NSEvent.ModifierFlags = []
        if carbonModifiers & cmdKey != 0 { flags.insert(.command) }
        if carbonModifiers & shiftKey != 0 { flags.insert(.shift) }
        if carbonModifiers & optionKey != 0 { flags.insert(.option) }
        if carbonModifiers & controlKey != 0 { flags.insert(.control) }
        return flags
    }
}
