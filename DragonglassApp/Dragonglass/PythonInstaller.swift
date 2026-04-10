import Foundation
import OSLog

private let logger = Logger(subsystem: subsystem, category: "BackendManager")

func getBundledPythonVersion() -> String? {
    guard let url = Bundle.main.url(forResource: "python_version", withExtension: "txt"),
          let version = try? String(contentsOf: url, encoding: .utf8) else {
        return nil
    }
    return version.trimmingCharacters(in: .whitespacesAndNewlines)
}

func getPythonVersion(at path: String) -> String? {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: path)
    process.arguments = ["-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"]
    let pipe = Pipe()
    process.standardOutput = pipe
    do {
        try process.run()
        process.waitUntilExit()
        if process.terminationStatus != 0 { return nil }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        return String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
    } catch {
        return nil
    }
}

func findPython3() -> String {
    let binaries = ["python3", "python3.14", "python3.13", "python3.12", "python3.11"]
    var candidatePaths = Set<String>()

    let extraPaths = [
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".pyenv/shims").path,
        FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".pyenv/bin").path,
        FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".conda/bin").path
    ]
    let augmentedPath = (extraPaths + (ProcessInfo.processInfo.environment["PATH"] ?? "")
        .components(separatedBy: ":")).joined(separator: ":")

    for bin in binaries {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        process.arguments = ["-a", bin]
        process.environment = ["PATH": augmentedPath]
        let pipe = Pipe()
        process.standardOutput = pipe
        try? process.run()
        process.waitUntilExit()

        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        if let output = String(data: data, encoding: .utf8) {
            for path in output.components(separatedBy: .newlines) {
                let trimmed = path.trimmingCharacters(in: .whitespacesAndNewlines)
                if !trimmed.isEmpty { candidatePaths.insert(trimmed) }
            }
        }
    }

    let homeDir = FileManager.default.homeDirectoryForCurrentUser
    var defaults = [
        "/usr/bin/python3",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        homeDir.appendingPathComponent(".conda/bin/python3").path,
        homeDir.appendingPathComponent(".pyenv/shims/python3").path
    ]
    for bin in binaries where bin != "python3" {
        defaults.append("/opt/homebrew/bin/\(bin)")
        defaults.append("/usr/local/bin/\(bin)")
        defaults.append(homeDir.appendingPathComponent(".pyenv/shims/\(bin)").path)
    }
    candidatePaths.formUnion(defaults)

    var candidates: [(path: String, version: String)] = []
    let requiredVersion = getBundledPythonVersion()

    if let required = requiredVersion {
        logger.info("Bundled wheels require Python \(required, privacy: .public)")
    }

    logger.info("Searching for compatible Python (3.11+)")
    for path in candidatePaths {
        if FileManager.default.fileExists(atPath: path) {
            if let version = getPythonVersion(at: path) {
                logger.debug("Found Python \(version, privacy: .public) at \(path, privacy: .public)")
                if let required = requiredVersion, version == required {
                    logger.info("Selected Python exact match path=\(path, privacy: .public) version=\(version, privacy: .public)")
                    return path
                }
                let v = version.split(separator: ".").compactMap { Int($0) }
                if v.count >= 2 && (v[0] > 3 || (v[0] == 3 && v[1] >= 11)) {
                    candidates.append((path, version))
                }
            }
        }
    }

    if candidates.isEmpty {
        logger.warning("No compatible Python 3.11+ found; using /usr/bin/python3")
        return "/usr/bin/python3"
    }

    var byMinor: [Int: (path: String, version: String)] = [:]
    for c in candidates {
        let parts = c.version.split(separator: ".").compactMap { Int($0) }
        guard parts.count >= 2 else { continue }
        let minor = parts[1]
        if byMinor[minor] == nil { byMinor[minor] = c }
    }

    let bundledMinor: Int
    if let required = requiredVersion,
       let m = required.split(separator: ".").compactMap({ Int($0) }).dropFirst().first {
        bundledMinor = m
    } else {
        bundledMinor = 11
    }

    let supportedMinors = binaries.compactMap { bin -> Int? in
        guard bin.hasPrefix("python3."), let m = Int(bin.dropFirst("python3.".count)) else { return nil }
        return m
    }
    let minMinor = supportedMinors.min() ?? bundledMinor
    let maxMinor = byMinor.keys.max() ?? bundledMinor

    var searchOrder: [Int] = [bundledMinor]
    let upperBound = max(bundledMinor, maxMinor)
    for v in (bundledMinor + 1)...max(bundledMinor + 1, upperBound) {
        searchOrder.append(v)
    }
    for v in stride(from: bundledMinor - 1, through: minMinor, by: -1) {
        searchOrder.append(v)
    }

    for minor in searchOrder {
        if let match = byMinor[minor] {
            logger.info("Selected Python path=\(match.path, privacy: .public) version=\(match.version, privacy: .public) bundled_minor=\(bundledMinor)")
            return match.path
        }
    }

    let best = candidates.first!
    logger.info("Selected Python fallback path=\(best.path, privacy: .public) version=\(best.version, privacy: .public)")
    return best.path
}

func installVenv(paths: BackendPaths) async throws {
    try FileManager.default.createDirectory(at: paths.appSupportDir, withIntermediateDirectories: true)

    let pythonPathForVenv = findPython3()
    logger.info("Creating venv using \(pythonPathForVenv, privacy: .public)")

    let venvProcess = Process()
    venvProcess.executableURL = URL(fileURLWithPath: pythonPathForVenv)
    venvProcess.arguments = ["-m", "venv", paths.venvDir.path]
    try await venvProcess.runAsync()

    if !FileManager.default.isExecutableFile(atPath: paths.uvPath.path) {
        let uvInstallProcess = Process()
        uvInstallProcess.executableURL = paths.pythonPath
        uvInstallProcess.arguments = ["-m", "pip", "install", "uv"]
        do {
            try await uvInstallProcess.runAsync()
        } catch {
            logger.warning("uv install failed, falling back to pip error=\(error.localizedDescription, privacy: .public)")
        }
    }

    guard let wheelDir = Bundle.main.url(forResource: "wheels", withExtension: nil) else {
        throw NSError(domain: "BackendManager", code: 1, userInfo: [NSLocalizedDescriptionKey: "Wheels not found in bundle"])
    }

    logger.info("Installing wheels from \(wheelDir.path, privacy: .public)")
    if FileManager.default.isExecutableFile(atPath: paths.uvPath.path) {
        let uvInstallProcess = Process()
        uvInstallProcess.executableURL = paths.uvPath
        uvInstallProcess.arguments = [
            "pip", "install",
            "--python", paths.pythonPath.path,
            "--no-index",
            "--find-links", wheelDir.path,
            "dragonglass"
        ]
        do {
            try await uvInstallProcess.runAsync()
            return
        } catch {
            logger.warning("uv package install failed, falling back to pip error=\(error.localizedDescription, privacy: .public)")
        }
    }

    let pipProcess = Process()
    pipProcess.executableURL = paths.pythonPath
    pipProcess.arguments = [
        "-m", "pip", "install",
        "--no-index",
        "--find-links", wheelDir.path,
        "dragonglass"
    ]
    try await pipProcess.runAsync()
}
