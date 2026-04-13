import Foundation
import OSLog

private let logger = Logger(subsystem: subsystem, category: "BundleInstaller")

enum BundleProgressEvent {
    case progress(message: String, fraction: Double)
    case done
    case error(String)
}

struct BundleInstaller {
    let paths: BackendPaths

    func install(
        appVersion: String,
        systemPython: String
    ) -> AsyncThrowingStream<BundleProgressEvent, Error> {
        AsyncThrowingStream { continuation in
            Task {
                do {
                    let srcPath = Bundle.main.url(forResource: "dragonglass_src", withExtension: nil)?.path ?? ""
                    let proc = Process()
                    proc.executableURL = URL(fileURLWithPath: systemPython)
                    let markerPath = paths.appSupportDir.appendingPathComponent("installed_bundle_version.txt").path
                    proc.arguments = [
                        "-m", "dragonglass.bundle",
                        "install",
                        "--version", appVersion,
                        "--venv-python", paths.pythonPath.path,
                        "--opencode-dir", paths.opencodeInstallDir.path,
                        "--marker-path", markerPath
                    ]
                    var env = ProcessInfo.processInfo.environment
                    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + (env["PATH"] ?? "")
                    env["PYTHONPATH"] = srcPath
                    proc.environment = env

                    let pipe = Pipe()
                    proc.standardOutput = pipe
                    proc.standardError = Pipe()

                    try proc.run()

                    let handle = pipe.fileHandleForReading
                    var buffer = Data()

                    while proc.isRunning || handle.availableData.count > 0 {
                        let chunk = handle.availableData
                        if chunk.isEmpty {
                            try await Task.sleep(for: .milliseconds(50))
                            continue
                        }
                        buffer.append(chunk)
                        while let newline = buffer.firstIndex(of: UInt8(ascii: "\n")) {
                            let lineData = buffer[buffer.startIndex..<newline]
                            buffer = buffer[buffer.index(after: newline)...]
                            if let event = parseProgressEvent(lineData) {
                                continuation.yield(event)
                                if case .done = event { break }
                                if case .error = event { break }
                            }
                        }
                    }

                    proc.waitUntilExit()
                    if proc.terminationStatus != 0 {
                        continuation.finish(throwing: NSError(
                            domain: "BundleInstaller",
                            code: Int(proc.terminationStatus),
                            userInfo: [NSLocalizedDescriptionKey: "Bundle install failed (exit \(proc.terminationStatus))"]
                        ))
                    } else {
                        continuation.finish()
                    }
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }

    func installOffline(
        bundlePath: URL,
        appVersion: String,
        systemPython: String
    ) -> AsyncThrowingStream<BundleProgressEvent, Error> {
        AsyncThrowingStream { continuation in
            Task {
                do {
                    let srcPath = Bundle.main.url(forResource: "dragonglass_src", withExtension: nil)?.path ?? ""
                    let proc = Process()
                    proc.executableURL = URL(fileURLWithPath: systemPython)
                    let markerPath = paths.appSupportDir.appendingPathComponent("installed_bundle_version.txt").path
                    proc.arguments = [
                        "-m", "dragonglass.bundle",
                        "install-offline",
                        bundlePath.path,
                        "--version", appVersion,
                        "--venv-python", paths.pythonPath.path,
                        "--opencode-dir", paths.opencodeInstallDir.path,
                        "--marker-path", markerPath
                    ]
                    var env = ProcessInfo.processInfo.environment
                    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + (env["PATH"] ?? "")
                    env["PYTHONPATH"] = srcPath
                    proc.environment = env

                    let pipe = Pipe()
                    proc.standardOutput = pipe
                    proc.standardError = Pipe()

                    try proc.run()
                    let handle = pipe.fileHandleForReading
                    var buffer = Data()

                    while proc.isRunning || handle.availableData.count > 0 {
                        let chunk = handle.availableData
                        if chunk.isEmpty {
                            try await Task.sleep(for: .milliseconds(50))
                            continue
                        }
                        buffer.append(chunk)
                        while let newline = buffer.firstIndex(of: UInt8(ascii: "\n")) {
                            let lineData = buffer[buffer.startIndex..<newline]
                            buffer = buffer[buffer.index(after: newline)...]
                            if let event = parseProgressEvent(lineData) {
                                continuation.yield(event)
                            }
                        }
                    }

                    proc.waitUntilExit()
                    if proc.terminationStatus != 0 {
                        continuation.finish(throwing: NSError(
                            domain: "BundleInstaller",
                            code: Int(proc.terminationStatus),
                            userInfo: [NSLocalizedDescriptionKey: "Offline install failed (exit \(proc.terminationStatus))"]
                        ))
                    } else {
                        continuation.finish()
                    }
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }
}

private func parseProgressEvent(_ data: Data) -> BundleProgressEvent? {
    guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let type_ = obj["type"] as? String else { return nil }
    switch type_ {
    case "progress":
        let message = obj["message"] as? String ?? ""
        let fraction = obj["fraction"] as? Double ?? 0
        return .progress(message: message, fraction: fraction)
    case "done":
        return .done
    case "error":
        let message = obj["message"] as? String ?? "unknown error"
        return .error(message)
    default:
        return nil
    }
}
