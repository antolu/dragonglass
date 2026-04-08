import Foundation
import OSLog

extension Process {
    func runAsync() async throws {
        let pipe = Pipe()
        self.standardOutput = pipe
        self.standardError = pipe

        try run()

        let handle = pipe.fileHandleForReading
        while isRunning {
            if let data = try? handle.read(upToCount: 4096), !data.isEmpty {
                if let str = String(data: data, encoding: .utf8) {
                    Logger(subsystem: subsystem, category: "BackendManager").debug("process output \(str)")
                }
            }
            try await Task.sleep(nanoseconds: 100_000_000)
        }

        if let data = try? handle.readToEnd(), !data.isEmpty {
            if let str = String(data: data, encoding: .utf8) {
                Logger(subsystem: subsystem, category: "BackendManager").debug("process output \(str)")
            }
        }

        if terminationStatus != 0 {
            throw NSError(domain: "Process", code: Int(terminationStatus), userInfo: [NSLocalizedDescriptionKey: "Process failed with status \(terminationStatus)"])
        }
    }
}

struct LsofProcessEntry {
    let pid: Int
    let command: String
    let processName: String
}

enum ProcessMatcher {
    case backend
    case mcp
}

func parseLsofProcessEntries(_ output: String) -> [LsofProcessEntry] {
    var entries: [LsofProcessEntry] = []
    var currentPid: Int?
    var currentCommand = ""

    for rawLine in output.components(separatedBy: .newlines) {
        if rawLine.isEmpty { continue }
        guard let prefix = rawLine.first else { continue }
        let value = String(rawLine.dropFirst())
        switch prefix {
        case "p":
            if let pid = currentPid {
                entries.append(LsofProcessEntry(pid: pid, command: currentCommand, processName: currentCommand.lowercased()))
            }
            currentPid = Int(value)
            currentCommand = ""
        case "c":
            currentCommand = value
        default:
            continue
        }
    }

    if let pid = currentPid {
        entries.append(LsofProcessEntry(pid: pid, command: currentCommand, processName: currentCommand.lowercased()))
    }
    return entries
}

func isExpectedProcess(_ process: LsofProcessEntry, matcher: ProcessMatcher) -> Bool {
    switch matcher {
    case .backend:
        return process.processName.contains("dragonglass") || process.processName.contains("python")
    case .mcp:
        return process.processName.contains("python") || process.processName.contains("uvicorn") || process.processName.contains("dragonglass")
    }
}

func killProcesses(onPort port: Int, label: String, matcher: ProcessMatcher) {
    let logger = Logger(subsystem: subsystem, category: "BackendManager")
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/sbin/lsof")
    process.arguments = ["-nP", "-iTCP:\(port)", "-sTCP:LISTEN", "-F", "pcn"]
    let pipe = Pipe()
    process.standardOutput = pipe
    try? process.run()
    process.waitUntilExit()

    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    guard let output = String(data: data, encoding: .utf8) else { return }

    let targets = parseLsofProcessEntries(output)

    for target in targets where isExpectedProcess(target, matcher: matcher) {
        logger.warning("Killing orphaned \(label) process pid=\(target.pid) command=\(target.command) port=\(port)")
        let killProcess = Process()
        killProcess.executableURL = URL(fileURLWithPath: "/bin/kill")
        killProcess.arguments = ["-9", "\(target.pid)"]
        try? killProcess.run()
        killProcess.waitUntilExit()
    }
}
