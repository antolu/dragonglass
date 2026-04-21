import Foundation
import OSLog

private let logger = Logger(subsystem: subsystem, category: "BackendManager")

func getMinPythonVersion() -> (major: Int, minor: Int) {
    guard let url = Bundle.main.url(forResource: "python_min_version", withExtension: "txt"),
          let raw = try? String(contentsOf: url, encoding: .utf8) else {
        return (3, 11)
    }
    let parts = raw.trimmingCharacters(in: .whitespacesAndNewlines).split(separator: ".").compactMap { Int($0) }
    guard parts.count >= 2 else { return (3, 11) }
    return (parts[0], parts[1])
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

func getSelectedPythonPath() -> String? {
    UserDefaults.standard.string(forKey: "selectedPythonPath")
}

func saveSelectedPythonPath(_ path: String) {
    UserDefaults.standard.set(path, forKey: "selectedPythonPath")
}

func discoverPythonCandidates() -> [(path: String, version: String)] {
    let homeDir = FileManager.default.homeDirectoryForCurrentUser
    let searchDirs = [
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        homeDir.appendingPathComponent(".pyenv/shims").path,
        homeDir.appendingPathComponent(".pyenv/bin").path,
        homeDir.appendingPathComponent(".conda/bin").path
    ]

    var candidatePaths = Set<String>()

    for dir in searchDirs {
        guard let entries = try? FileManager.default.contentsOfDirectory(atPath: dir) else { continue }
        for entry in entries where entry == "python3" || entry.wholeMatch(of: /python3\.\d+/) != nil {
            candidatePaths.insert("\(dir)/\(entry)")
        }
    }

    let minVersion = getMinPythonVersion()
    var candidates: [(path: String, version: String)] = []
    for path in candidatePaths {
        guard FileManager.default.fileExists(atPath: path),
              let version = getPythonVersion(at: path) else { continue }
        let v = version.split(separator: ".").compactMap { Int($0) }
        guard v.count >= 2 else { continue }
        let meetsMin = v[0] > minVersion.major || (v[0] == minVersion.major && v[1] >= minVersion.minor)
        guard meetsMin else { continue }
        if !candidates.contains(where: { $0.path == path }) {
            candidates.append((path, version))
        }
    }
    return candidates.sorted { $0.version > $1.version }
}

func findPython3() -> String {
    discoverPythonCandidates().first?.path ?? "/usr/bin/python3"
}
