import Foundation
import os

private let logger = Logger(subsystem: "com.antolu.dragonglass", category: "DictationKeyRemapper")

// Remaps the Siri/Dictation key (HID consumer page usage 0xCF) to F13 (0x700000068)
// via hidutil. No persistent effect; must be called on every launch.
func remapDictationKeyToF13() {
    let mapping = #"{"UserKeyMapping":[{"HIDKeyboardModifierMappingSrc":0xC000000CF,"HIDKeyboardModifierMappingDst":0x700000072}]}"#
    let proc = Process()
    proc.executableURL = URL(fileURLWithPath: "/usr/bin/hidutil")
    proc.arguments = ["property", "--set", mapping]
    let pipe = Pipe()
    proc.standardOutput = pipe
    proc.standardError = pipe
    do {
        try proc.launch()
        proc.waitUntilExit()
        if proc.terminationStatus == 0 {
            logger.info("Dictation key remapped via hidutil")
        } else {
            let output = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            logger.warning("hidutil remap failed (status \(proc.terminationStatus)): \(output)")
        }
    } catch {
        logger.error("Failed to launch hidutil: \(error.localizedDescription)")
    }
}
