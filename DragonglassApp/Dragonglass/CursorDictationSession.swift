import AppKit
import os
import UserNotifications

private let logger = Logger(subsystem: "com.antolu.dragonglass", category: "CursorDictationSession")

@MainActor
final class CursorDictationSession {
    private let element: AXUIElement
    private let anchor: Int
    private var lastInsertedLength = 0
    let isInSelf: Bool

    private init(element: AXUIElement, anchor: Int, isInSelf: Bool) {
        self.element = element
        self.anchor = anchor
        self.isInSelf = isInSelf
    }

    static func start() -> CursorDictationSession? {
        let systemElement = AXUIElementCreateSystemWide()
        var focusedRef: CFTypeRef?
        guard AXUIElementCopyAttributeValue(systemElement, kAXFocusedUIElementAttribute as CFString, &focusedRef) == .success,
              let focusedRef else {
            logger.warning("No focused AX element")
            return nil
        }
        // swiftlint:disable:next force_cast
        let element = focusedRef as! AXUIElement

        var rangeRef: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, kAXSelectedTextRangeAttribute as CFString, &rangeRef) == .success,
              let rangeRef else {
            logger.warning("Cannot read selection range from focused element")
            notifyUnsupported(element: element)
            return nil
        }

        var cfRange = CFRange(location: 0, length: 0)
        // swiftlint:disable:next force_cast
        guard AXValueGetValue(rangeRef as! AXValue, .cfRange, &cfRange) else {
            logger.warning("Cannot extract CFRange from AX value")
            return nil
        }
        let anchor = cfRange.location + cfRange.length

        // Probe write support with a no-op selection move
        var probeRange = CFRange(location: anchor, length: 0)
        guard let probeValue = AXValueCreate(.cfRange, &probeRange) else { return nil }
        let writeResult = AXUIElementSetAttributeValue(element, kAXSelectedTextRangeAttribute as CFString, probeValue)
        if writeResult != .success {
            logger.warning("AX write not supported: \(writeResult.rawValue)")
            notifyUnsupported(element: element)
            return nil
        }

        var pid: pid_t = 0
        AXUIElementGetPid(element, &pid)
        let isInSelf = NSRunningApplication(processIdentifier: pid)?.bundleIdentifier == Bundle.main.bundleIdentifier

        logger.info("CursorDictationSession started at anchor \(anchor), inSelf=\(isInSelf)")
        return CursorDictationSession(element: element, anchor: anchor, isInSelf: isInSelf)
    }

    func update(text: String) {
        var replaceRange = CFRange(location: anchor, length: lastInsertedLength)
        guard let axRange = AXValueCreate(.cfRange, &replaceRange) else { return }
        AXUIElementSetAttributeValue(element, kAXSelectedTextRangeAttribute as CFString, axRange)
        AXUIElementSetAttributeValue(element, kAXSelectedTextAttribute as CFString, text as CFString)
        lastInsertedLength = (text as NSString).length
    }

    func finish() {
        guard lastInsertedLength > 0 else { return }
        var endRange = CFRange(location: anchor + lastInsertedLength, length: 0)
        if let axRange = AXValueCreate(.cfRange, &endRange) {
            AXUIElementSetAttributeValue(element, kAXSelectedTextRangeAttribute as CFString, axRange)
        }
    }

    func checkDrift() -> Bool {
        var rangeRef: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, kAXSelectedTextRangeAttribute as CFString, &rangeRef) == .success,
              let rangeRef else { return false }
        var cfRange = CFRange(location: 0, length: 0)
        // swiftlint:disable:next force_cast
        guard AXValueGetValue(rangeRef as! AXValue, .cfRange, &cfRange) else { return false }
        let expectedCursor = anchor + lastInsertedLength
        let drifted = cfRange.location != expectedCursor
        if drifted { logger.info("Drift: expected \(expectedCursor), got \(cfRange.location)") }
        return drifted
    }

    private static func notifyUnsupported(element: AXUIElement) {
        var pid: pid_t = 0
        AXUIElementGetPid(element, &pid)
        guard let app = NSRunningApplication(processIdentifier: pid) else { return }
        let bundleID = app.bundleIdentifier ?? "unknown.\(pid)"
        let appName = app.localizedName ?? bundleID

        var seen = UserDefaults.standard.stringArray(forKey: "axUnsupportedApps") ?? []
        guard !seen.contains(bundleID) else { return }
        seen.append(bundleID)
        UserDefaults.standard.set(seen, forKey: "axUnsupportedApps")

        let content = UNMutableNotificationContent()
        content.title = "Dictation unavailable"
        content.body = "\(appName) doesn't support live dictation."
        let request = UNNotificationRequest(identifier: "ax-unsupported-\(bundleID)", content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request) { error in
            if let error { logger.error("Notification error: \(error.localizedDescription)") }
        }
    }
}
