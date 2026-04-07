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
        guard AXIsProcessTrusted() else {
            logger.warning("registerIfPossible: not AX trusted, tap not installed")
            return
        }
        let popoverkeyCode = UserDefaults.standard.integer(forKey: "sttHotkeyKeyCode")
        let popoverModifiers = UserDefaults.standard.integer(forKey: "sttHotkeyModifiers")
        let dictationKeyCode = UserDefaults.standard.integer(forKey: "dictationHotkeyKeyCode")
        let dictationModifiers = UserDefaults.standard.integer(forKey: "dictationHotkeyModifiers")
        logger.debug("registerIfPossible: popover=\(popoverkeyCode) dictation=\(dictationKeyCode)")
        installEventTap(
            popoverKeyCode: popoverkeyCode, popoverModifiers: popoverModifiers,
            dictationKeyCode: dictationKeyCode, dictationModifiers: dictationModifiers
        )
    }

    private func installEventTap(popoverKeyCode: Int, popoverModifiers: Int, dictationKeyCode: Int, dictationModifiers: Int) {
        let mask: CGEventMask =
            (1 << CGEventType.keyDown.rawValue) |
            (1 << CGEventType.keyUp.rawValue) |
            (1 << CGEventType.flagsChanged.rawValue)

        let callback: CGEventTapCallBack = { _, type, event, userInfo -> Unmanaged<CGEvent>? in
            guard let userInfo else { return Unmanaged.passUnretained(event) }
            let ctx = Unmanaged<TapContext>.fromOpaque(userInfo).takeUnretainedValue()
            return ctx.handle(type: type, event: event)
        }

        let ctx = TapContext(
            popover: TapContext.KeyBinding(keyCode: popoverKeyCode, carbonModifiers: popoverModifiers),
            dictation: TapContext.KeyBinding(keyCode: dictationKeyCode, carbonModifiers: dictationModifiers),
            manager: self
        )
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
            logger.error("CGEvent.tapCreate failed — check Input Monitoring permission")
            return
        }
        logger.info("CGEvent tap installed successfully")

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
        if sttManager?.isRecording == true {
            sttManager?.stopAndTranscribe()
        } else {
            agentClient?.startNewChat()
            menuBarManager?.showPopover()
            sttManager?.startRecording()
        }
    }

    var dictationToggleThreshold: Double {
        UserDefaults.standard.object(forKey: "dictationToggleThreshold") as? Double ?? 10.0
    }

    private var dictationKeyDownTime: Double = 0

    func onDictationKeyDown() {
        logger.debug("onDictationKeyDown: sttManager=\(self.sttManager != nil), isCursorDictating=\(self.sttManager?.isCursorDictating ?? false)")
        if sttManager?.isCursorDictating == true {
            sttManager?.stopCursorDictation()
            dictationKeyDownTime = 0
        } else {
            dictationKeyDownTime = CACurrentMediaTime()
            sttManager?.startCursorDictation()
        }
    }

    func onDictationKeyUp() {
        guard sttManager?.isCursorDictating == true, dictationKeyDownTime > 0 else { return }
        let held = CACurrentMediaTime() - dictationKeyDownTime
        let threshold = dictationToggleThreshold
        if threshold == 0 || held < threshold {
            sttManager?.stopCursorDictation()
            dictationKeyDownTime = 0
        }
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
    struct KeyBinding {
        var isPressed = false
        let keyCode: Int
        let carbonModifiers: Int
    }

    var popover: KeyBinding
    var dictation: KeyBinding
    weak var manager: HotkeyManager?

    init(popover: KeyBinding, dictation: KeyBinding, manager: HotkeyManager) {
        self.popover = popover
        self.dictation = dictation
        self.manager = manager
    }

    func handle(type: CGEventType, event: CGEvent) -> Unmanaged<CGEvent>? {
        let keyCode = Int(event.getIntegerValueField(.keyboardEventKeycode))
        let cgFlags = event.flags
        let nsFlags = NSEvent.ModifierFlags(rawValue: UInt(cgFlags.rawValue))
        let eventCarbon = HotkeyManager.toCarbonModifiers(nsFlags)
        let isRepeat = event.getIntegerValueField(.keyboardEventAutorepeat) != 0

        switch type {
        case .keyDown:
            // Popover hotkey
            if popover.keyCode != 0, keyCode == popover.keyCode, eventCarbon == popover.carbonModifiers {
                if isRepeat || popover.isPressed { return nil }
                popover.isPressed = true
                Task { @MainActor [weak manager] in manager?.onKeyDown() }
                return nil
            }
            // Dictation hotkey
            if dictation.keyCode != 0, keyCode == dictation.keyCode, eventCarbon == dictation.carbonModifiers {
                if isRepeat { return nil }
                if !dictation.isPressed {
                    dictation.isPressed = true
                    Task { @MainActor [weak manager] in manager?.onDictationKeyDown() }
                }
                return nil
            }
            return Unmanaged.passUnretained(event)

        case .keyUp:
            if popover.keyCode != 0, keyCode == popover.keyCode, popover.isPressed {
                popover.isPressed = false
                return nil
            }
            if dictation.keyCode != 0, keyCode == dictation.keyCode, dictation.isPressed {
                dictation.isPressed = false
                Task { @MainActor [weak manager] in manager?.onDictationKeyUp() }
                return nil
            }
            return Unmanaged.passUnretained(event)

        case .flagsChanged:
            if popover.isPressed {
                let required = HotkeyManager.toNSModifiers(carbonModifiers: popover.carbonModifiers)
                if !nsFlags.contains(required) { popover.isPressed = false }
            }
            if dictation.isPressed {
                let required = HotkeyManager.toNSModifiers(carbonModifiers: dictation.carbonModifiers)
                if !nsFlags.contains(required) {
                    dictation.isPressed = false
                    Task { @MainActor [weak manager] in manager?.onDictationKeyUp() }
                }
            }
            return Unmanaged.passUnretained(event)

        default:
            return Unmanaged.passUnretained(event)
        }
    }
}
