import Foundation
import Combine

enum BackendPhase: Equatable {
    case installing
    case starting
    case ready
    case failed(String)
}

@MainActor
class BackendManager: ObservableObject {
    @Published var phase: BackendPhase = .starting
    private var process: Process?

    private let appSupportDir: URL = {
        let paths = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
        return paths[0].appendingPathComponent("dragonglass")
    }()

    private var venvDir: URL { appSupportDir.appendingPathComponent("venv") }
    private var pythonPath: URL { venvDir.appendingPathComponent("bin/python3") }
    private var dragonglassPath: URL { venvDir.appendingPathComponent("bin/dragonglass") }

    init() {
        Task {
            await startBackend()
        }
    }

    func startBackend() async {
        await findAndKillExistingBackend()

        let bundledVersion = getBundledVersion()
        let installedVersion = getInstalledVersion()

        let needsInstall = !FileManager.default.fileExists(atPath: dragonglassPath.path) || (bundledVersion != nil && bundledVersion != installedVersion)

        if needsInstall {
            phase = .installing
            do {
                if FileManager.default.fileExists(atPath: venvDir.path) {
                    try? FileManager.default.removeItem(at: venvDir)
                }
                try await installVenv()
                if let version = bundledVersion {
                    try? version.write(to: appSupportDir.appendingPathComponent("installed_version.txt"), atomically: true, encoding: .utf8)
                }
            } catch {
                phase = .failed("Installation failed: \(error.localizedDescription)")
                return
            }
        }

        phase = .starting
        do {
            try launchProcess()
            phase = .ready
        } catch {
            phase = .failed("Launch failed: \(error.localizedDescription)")
        }
    }

    private func getBundledVersion() -> String? {
        guard let url = Bundle.main.url(forResource: "version", withExtension: "txt"),
              let version = try? String(contentsOf: url, encoding: .utf8) else {
            return nil
        }
        return version.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func getInstalledVersion() -> String? {
        let url = appSupportDir.appendingPathComponent("installed_version.txt")
        guard let version = try? String(contentsOf: url, encoding: .utf8) else {
            return nil
        }
        return version.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func findAndKillExistingBackend() async {
        let pathUrl = dragonglassPath
        await Task.detached {
            // 1. Try graceful shutdown first
            let stopProcess = Process()
            stopProcess.executableURL = pathUrl
            stopProcess.arguments = ["stop"]
            try? stopProcess.run()
            stopProcess.waitUntilExit()

            // Brief pause to allow graceful shutdown
            Thread.sleep(forTimeInterval: 0.5)

            // 2. Fallback to hard kill for any stragglers
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/sbin/lsof")
            process.arguments = ["-ti:51363"]
            let pipe = Pipe()
            process.standardOutput = pipe
            try? process.run()
            process.waitUntilExit()

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8) {
                let pids = output.components(separatedBy: .newlines).compactMap { Int($0.trimmingCharacters(in: .whitespacesAndNewlines)) }
                for pid in pids {
                    print("[BackendManager] Killing orphaned backend process PID \(pid)")
                    let killProcess = Process()
                    killProcess.executableURL = URL(fileURLWithPath: "/bin/kill")
                    killProcess.arguments = ["-9", "\(pid)"]
                    try? killProcess.run()
                    killProcess.waitUntilExit()
                }
            }
        }.value
    }

    private func findPython3() -> String {
        let binaries = ["python3", "python3.14", "python3.13", "python3.12", "python3.11"]
        var candidatePaths = Set<String>()

        // 1. Try which -a for common names
        for bin in binaries {
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
            process.arguments = ["which", "-a", bin]
            let pipe = Pipe()
            process.standardOutput = pipe
            try? process.run()
            process.waitUntilExit()

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8) {
                for path in output.components(separatedBy: .newlines) {
                    let trimmed = path.trimmingCharacters(in: .whitespacesAndNewlines)
                    if !trimmed.isEmpty {
                        candidatePaths.insert(trimmed)
                    }
                }
            }
        }

        // 2. Add some hardcoded defaults just in case
        let defaults = [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
            FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".conda/bin/python3").path
        ]
        candidatePaths.formUnion(defaults)

        var candidates: [(path: String, version: String)] = []
        let requiredVersion = getBundledPythonVersion()

        if let required = requiredVersion {
            print("[BackendManager] Bundled wheels require Python \(required)")
        }

        print("[BackendManager] Searching for compatible Python (3.11+)...")
        for path in candidatePaths {
            if FileManager.default.fileExists(atPath: path) {
                if let version = getPythonVersion(at: path) {
                    print("[BackendManager] Found Python \(version) at \(path)")
                    if let required = requiredVersion, version == required {
                        print("[BackendManager] Selected \(path) (exact match)")
                        return path
                    }

                    let v = version.split(separator: ".").compactMap { Int($0) }
                    if v.count >= 2 && (v[0] > 3 || (v[0] == 3 && v[1] >= 11)) {
                        candidates.append((path, version))
                    }
                }
            }
        }

        // Sort candidates by version (descending)
        candidates.sort { a, b in
            let va = a.version.split(separator: ".").compactMap { Int($0) }
            let vb = b.version.split(separator: ".").compactMap { Int($0) }
            for i in 0..<min(va.count, vb.count) {
                if va[i] != vb[i] { return va[i] > vb[i] }
            }
            return va.count > vb.count
        }

        if let best = candidates.first {
            print("[BackendManager] Selected \(best.path) (highest compatible version \(best.version))")
            return best.path
        }

        print("[BackendManager] No compatible Python 3.11+ found, falling back to /usr/bin/python3")
        return "/usr/bin/python3"
    }

    private func getPythonVersion(at path: String) -> String? {
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

    private func getBundledPythonVersion() -> String? {
        guard let url = Bundle.main.url(forResource: "python_version", withExtension: "txt"),
              let version = try? String(contentsOf: url, encoding: .utf8) else {
            return nil
        }
        return version.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func installVenv() async throws {
        try FileManager.default.createDirectory(at: appSupportDir, withIntermediateDirectories: true)

        let pythonPathForVenv = findPython3()
        print("[BackendManager] Creating venv using \(pythonPathForVenv)...")

        // 1. Create venv
        let venvProcess = Process()
        venvProcess.executableURL = URL(fileURLWithPath: pythonPathForVenv)
        venvProcess.arguments = ["-m", "venv", venvDir.path]
        try await venvProcess.runAsync()

        // 2. Install wheel from bundle
        guard let wheelDir = Bundle.main.url(forResource: "wheels", withExtension: nil) else {
            throw NSError(domain: "BackendManager", code: 1, userInfo: [NSLocalizedDescriptionKey: "Wheels not found in bundle"])
        }

        print("[BackendManager] Installing wheels from \(wheelDir.path)...")
        let pipProcess = Process()
        pipProcess.executableURL = pythonPath
        pipProcess.arguments = [
            "-m", "pip", "install",
            "--no-index",
            "--find-links", wheelDir.path,
            "dragonglass"
        ]
        try await pipProcess.runAsync()
    }

    private func launchProcess() throws {
        let p = Process()
        p.executableURL = dragonglassPath
        p.arguments = ["serve"]

        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = pipe

        // Start a thread or task to read the pipe
        let handle = pipe.fileHandleForReading
        handle.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty, let str = String(data: data, encoding: .utf8) {
                print("[Backend] \(str)", terminator: "")
            }
        }

        p.terminationHandler = { [weak self] process in
            Task { @MainActor in
                if self?.process == process {
                    self?.phase = .failed("Backend exited with code \(process.terminationStatus)")
                }
            }
        }

        self.process = p
        try p.run()
    }

    deinit {
        process?.terminate()
    }
}

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
                    print(str, terminator: "")
                }
            }
            try await Task.sleep(nanoseconds: 100_000_000)
        }

        // Read remaining
        if let data = try? handle.readToEnd(), !data.isEmpty {
            if let str = String(data: data, encoding: .utf8) {
                print(str, terminator: "")
            }
        }

        if terminationStatus != 0 {
            throw NSError(domain: "Process", code: Int(terminationStatus), userInfo: [NSLocalizedDescriptionKey: "Process failed with status \(terminationStatus)"])
        }
    }
}
