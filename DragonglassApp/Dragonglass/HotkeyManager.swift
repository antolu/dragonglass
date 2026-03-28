import AppKit
import Carbon
import Combine

@MainActor
final class HotkeyManager: NSObject, ObservableObject {
    @Published var accessibilityGranted = false

    private weak var sttManager: STTManager?
    private weak var menuBarManager: MenuBarManager?

    private var hotKeyRef: EventHotKeyRef?
    private var eventHandlerRef: EventHandlerRef?
    private var keyUpMonitor: Any?
    private var currentKeyCode: Int = 0

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
        currentKeyCode = keyCode
        register(keyCode: UInt32(keyCode), carbonModifiers: UInt32(modifiers))
    }

    private func register(keyCode: UInt32, carbonModifiers: UInt32) {
        let hotKeyID = EventHotKeyID(signature: 0x4452474C, id: 1)
        var ref: EventHotKeyRef?
        RegisterEventHotKey(keyCode, carbonModifiers, hotKeyID, GetEventDispatcherTarget(), 0, &ref)
        hotKeyRef = ref

        var eventType = EventTypeSpec(
            eventClass: OSType(kEventClassKeyboard),
            eventKind: UInt32(kEventHotKeyPressed)
        )
        let callback: EventHandlerUPP = { _, _, userData -> OSStatus in
            guard let userData else { return OSStatus(eventNotHandledErr) }
            let manager = Unmanaged<HotkeyManager>.fromOpaque(userData).takeUnretainedValue()
            Task { @MainActor in manager.onKeyDown() }
            return noErr
        }
        let status = InstallEventHandler(
            GetEventDispatcherTarget(),
            callback,
            1, &eventType,
            Unmanaged.passUnretained(self).toOpaque(),
            &eventHandlerRef
        )
        if status != noErr {
            print("[HotkeyManager] InstallEventHandler failed: \(status)")
        }

        keyUpMonitor = NSEvent.addGlobalMonitorForEvents(matching: .keyUp) { [weak self] event in
            guard let self, Int(event.keyCode) == self.currentKeyCode else { return }
            Task { @MainActor in self.onKeyUp() }
        }
    }

    private func unregister() {
        if let ref = hotKeyRef { UnregisterEventHotKey(ref); hotKeyRef = nil }
        if let ref = eventHandlerRef { RemoveEventHandler(ref); eventHandlerRef = nil }
        if let mon = keyUpMonitor { NSEvent.removeMonitor(mon); keyUpMonitor = nil }
    }

    func onKeyDown() {
        sttManager?.startRecording()
        menuBarManager?.showPopover()
    }

    func onKeyUp() {
        sttManager?.stopAndTranscribe()
    }

    static func toCarbonModifiers(_ flags: NSEvent.ModifierFlags) -> Int {
        var carbon = 0
        if flags.contains(.command) { carbon |= cmdKey }
        if flags.contains(.shift) { carbon |= shiftKey }
        if flags.contains(.option) { carbon |= optionKey }
        if flags.contains(.control) { carbon |= controlKey }
        return carbon
    }
}
