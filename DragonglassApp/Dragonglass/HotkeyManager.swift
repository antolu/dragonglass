import AppKit
import Carbon
import Combine
import os

private let logger = Logger(subsystem: "com.antolu.dragonglass", category: "HotkeyManager")

@MainActor
final class HotkeyManager: NSObject, ObservableObject {
    @Published var accessibilityGranted = false

    private weak var sttManager: STTManager?
    private weak var menuBarManager: MenuBarManager?
    private weak var agentClient: AgentClient?

    private var eventTap: CFMachPort?
    private var runLoopSource: CFRunLoopSource?

    func setup(sttManager: STTManager, menuBarManager: MenuBarManager, agentClient: AgentClient) {
        self.sttManager = sttManager
        self.menuBarManager = menuBarManager
        self.agentClient = agentClient
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
        installEventTap(keyCode: keyCode, carbonModifiers: modifiers)
    }

    private func installEventTap(keyCode: Int, carbonModifiers: Int) {
        let mask: CGEventMask =
            (1 << CGEventType.keyDown.rawValue) |
            (1 << CGEventType.keyUp.rawValue) |
            (1 << CGEventType.flagsChanged.rawValue)

        let callback: CGEventTapCallBack = { _, type, event, userInfo -> Unmanaged<CGEvent>? in
            guard let userInfo else { return Unmanaged.passUnretained(event) }
            let ctx = Unmanaged<TapContext>.fromOpaque(userInfo).takeUnretainedValue()
            return ctx.handle(type: type, event: event)
        }

        let ctx = TapContext(state: TapContext.TapState(keyCode: keyCode, carbonModifiers: carbonModifiers), manager: self)
        let ctxPtr = Unmanaged.passRetained(ctx)

        guard let tap = CGEvent.tapCreate(
            tap: .cgSessionEventTap,
            place: .headInsertEventTap,
            options: .defaultTap,
            eventsOfInterest: mask,
            callback: callback,
            userInfo: ctxPtr.toOpaque()
        ) else {
            ctxPtr.release()
            print("[HotkeyManager] CGEvent.tapCreate failed — check Input Monitoring permission")
            return
        }

        eventTap = tap
        let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)
        runLoopSource = source
        CFRunLoopAddSource(CFRunLoopGetMain(), source, .commonModes)
        CGEvent.tapEnable(tap: tap, enable: true)
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
    }

    func onKeyDown() {
        agentClient?.startNewChat()
        menuBarManager?.showPopover()
        sttManager?.startRecording()
    }

    func onKeyUp() {
        sttManager?.stopAndTranscribe()
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

private final class TapContext: @unchecked Sendable {
    final class TapState: @unchecked Sendable {
        var isPressed = false
        let keyCode: Int
        let carbonModifiers: Int
        init(keyCode: Int, carbonModifiers: Int) {
            self.keyCode = keyCode
            self.carbonModifiers = carbonModifiers
        }
    }

    let state: TapState
    weak var manager: HotkeyManager?

    init(state: TapState, manager: HotkeyManager) {
        self.state = state
        self.manager = manager
    }

    func handle(type: CGEventType, event: CGEvent) -> Unmanaged<CGEvent>? {
        let keyCode = Int(event.getIntegerValueField(.keyboardEventKeycode))
        let cgFlags = event.flags
        let nsFlags = NSEvent.ModifierFlags(rawValue: UInt(cgFlags.rawValue))
        let eventCarbon = HotkeyManager.toCarbonModifiers(nsFlags)

        switch type {
        case .keyDown:
            guard keyCode == state.keyCode, eventCarbon == state.carbonModifiers else {
                return Unmanaged.passUnretained(event)
            }
            let isRepeat = event.getIntegerValueField(.keyboardEventAutorepeat) != 0
            if isRepeat || state.isPressed { return nil }
            logger.debug("keyDown matched at \(CACurrentMediaTime())")
            state.isPressed = true
            Task { @MainActor [weak manager] in manager?.onKeyDown() }
            return nil

        case .keyUp:
            guard keyCode == state.keyCode, state.isPressed else {
                return Unmanaged.passUnretained(event)
            }
            logger.debug("keyUp matched at \(CACurrentMediaTime())")
            state.isPressed = false
            Task { @MainActor [weak manager] in manager?.onKeyUp() }
            return nil

        case .flagsChanged:
            guard state.isPressed else { return Unmanaged.passUnretained(event) }
            let requiredNSFlags = HotkeyManager.toNSModifiers(carbonModifiers: state.carbonModifiers)
            if !nsFlags.contains(requiredNSFlags) {
                state.isPressed = false
                Task { @MainActor [weak manager] in manager?.onKeyUp() }
            }
            return Unmanaged.passUnretained(event)

        default:
            return Unmanaged.passUnretained(event)
        }
    }
}
