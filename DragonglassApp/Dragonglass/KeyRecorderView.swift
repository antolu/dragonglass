import AppKit
import Carbon
import SwiftUI

struct KeyRecorderView: NSViewRepresentable {
    @Binding var keyCode: Int
    @Binding var modifiers: Int
    var onChanged: () -> Void

    func makeNSView(context: Context) -> KeyRecorderNSView {
        let v = KeyRecorderNSView()
        v.coordinator = context.coordinator
        return v
    }

    func updateNSView(_ nsView: KeyRecorderNSView, context: Context) {
        nsView.keyCode = keyCode
        nsView.modifiers = modifiers
        nsView.needsDisplay = true
    }

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    class Coordinator {
        var parent: KeyRecorderView
        init(_ p: KeyRecorderView) { parent = p }

        func record(keyCode: UInt16, modifierFlags: NSEvent.ModifierFlags) {
            parent.keyCode = Int(keyCode)
            parent.modifiers = HotkeyManager.toCarbonModifiers(modifierFlags)
            parent.onChanged()
        }
    }
}

class KeyRecorderNSView: NSView {
    var coordinator: KeyRecorderView.Coordinator?
    var keyCode: Int = 0
    var modifiers: Int = 0
    private var isRecording = false

    override var acceptsFirstResponder: Bool { true }

    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)
        NSColor.controlBackgroundColor.setFill()
        let path = NSBezierPath(roundedRect: bounds, xRadius: 4, yRadius: 4)
        path.fill()
        NSColor.separatorColor.setStroke()
        path.lineWidth = 1
        path.stroke()

        let text = displayString()
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 12),
            .foregroundColor: isRecording ? NSColor.controlAccentColor : NSColor.labelColor,
        ]
        let str = NSAttributedString(string: text, attributes: attrs)
        let size = str.size()
        let origin = CGPoint(x: (bounds.width - size.width) / 2, y: (bounds.height - size.height) / 2)
        str.draw(at: origin)
    }

    override func mouseDown(with event: NSEvent) {
        isRecording = true
        window?.makeFirstResponder(self)
        needsDisplay = true
    }

    private let modifierOnlyCodes: Set<UInt16> = [54, 55, 56, 57, 58, 59, 60, 61, 62, 63]

    override func keyDown(with event: NSEvent) {
        guard isRecording, !modifierOnlyCodes.contains(event.keyCode) else { return }
        coordinator?.record(keyCode: event.keyCode, modifierFlags: event.modifierFlags)
        keyCode = Int(event.keyCode)
        modifiers = HotkeyManager.toCarbonModifiers(event.modifierFlags)
        isRecording = false
        needsDisplay = true
    }

    override func resignFirstResponder() -> Bool {
        if isRecording { isRecording = false; needsDisplay = true }
        return super.resignFirstResponder()
    }

    private func displayString() -> String {
        if isRecording { return "Press a key…" }
        if keyCode == 0 { return "Click to set" }
        return modifierString() + keyString()
    }

    private func modifierString() -> String {
        var s = ""
        if modifiers & controlKey != 0 { s += "^" }
        if modifiers & optionKey != 0 { s += "⌥" }
        if modifiers & shiftKey != 0 { s += "⇧" }
        if modifiers & cmdKey != 0 { s += "⌘" }
        return s
    }

    private func keyString() -> String {
        let named: [Int: String] = [
            36: "↩", 48: "⇥", 49: "Space", 51: "⌫", 53: "⎋",
            123: "←", 124: "→", 125: "↓", 126: "↑",
            122: "F1", 120: "F2", 99: "F3", 118: "F4", 96: "F5",
            97: "F6", 98: "F7", 100: "F8", 101: "F9", 109: "F10",
            103: "F11", 111: "F12",
        ]
        if let name = named[keyCode] { return name }
        if let char = characterForKeyCode(UInt16(keyCode)) { return char.uppercased() }
        return "(\(keyCode))"
    }

    private func characterForKeyCode(_ keyCode: UInt16) -> String? {
        guard let kbd = TISCopyCurrentKeyboardLayoutInputSource()?.takeRetainedValue(),
              let layoutData = TISGetInputSourceProperty(kbd, kTISPropertyUnicodeKeyLayoutData) else { return nil }
        let dataRef = unsafeBitCast(layoutData, to: CFData.self)
        let layout = unsafeBitCast(CFDataGetBytePtr(dataRef), to: UnsafePointer<UCKeyboardLayout>.self)
        var dead: UInt32 = 0
        var chars = [UniChar](repeating: 0, count: 4)
        var length = 0
        UCKeyTranslate(layout, keyCode, UInt16(kUCKeyActionDisplay), 0,
                       UInt32(LMGetKbdType()), OptionBits(kUCKeyTranslateNoDeadKeysMask),
                       &dead, 4, &length, &chars)
        guard length > 0 else { return nil }
        return String(utf16CodeUnits: Array(chars.prefix(length)), count: length)
    }
}
