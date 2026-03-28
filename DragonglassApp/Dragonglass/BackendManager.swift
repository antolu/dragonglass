import Foundation
import Combine
import OSLog

private let logger = Logger(subsystem: "com.lua.Dragonglass", category: "BackendManager")

enum BackendPhase: Equatable {
    case installing
    case starting
    case ready
    case needsPluginUpdate(String, String)  // (installedVersion, bundledVersion)
    case needsPluginReload
    case obsidianUnreachable
    case obsidianVersionMismatch(String)
    case failed(String)
}

@MainActor
class BackendManager: ObservableObject {
    @Published var phase: BackendPhase = .starting
    @Published var obsidianWarning: String? = nil
    private var process: Process?
    private var obsidianPollTask: Task<Void, Never>?

    private let appSupportDir: URL = {
        let paths = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
        return paths[0].appendingPathComponent("dragonglass")
    }()

    private var venvDir: URL { appSupportDir.appendingPathComponent("venv") }
    private var pythonPath: URL { venvDir.appendingPathComponent("bin/python3") }
    private var uvPath: URL { venvDir.appendingPathComponent("bin/uv") }
    private var dragonglassPath: URL { venvDir.appendingPathComponent("bin/dragonglass") }
    private var opencodeInstallDir: URL { appSupportDir.appendingPathComponent("opencode") }
    private var opencodeBinPath: URL {
        opencodeInstallDir.appendingPathComponent("node_modules/.bin/opencode")
    }
    private var opencodeCliPackagePath: URL {
        opencodeInstallDir.appendingPathComponent("node_modules/opencode-ai/package.json")
    }
    private var opencodeConfigPath: URL {
        appSupportDir.appendingPathComponent("config/opencode.json")
    }

    init() {
        Task {
            await startBackend()
        }
    }

    func startBackend() async {
        await findAndKillExistingBackend()

        guard let bundledVersion = getBundledVersion() else {
            phase = .failed("Missing bundled backend version metadata (version.txt). Rebuild app.")
            return
        }
        guard getBundledPythonVersion() != nil else {
            phase = .failed("Missing bundled python metadata (python_version.txt). Rebuild app.")
            return
        }
        guard Bundle.main.url(forResource: "wheels", withExtension: nil) != nil else {
            phase = .failed("Missing bundled wheels directory. Rebuild app.")
            return
        }
        let installedVersion = getInstalledVersion()

        let needsInstall = !FileManager.default.fileExists(atPath: dragonglassPath.path)
            || bundledVersion != installedVersion

        if needsInstall {
            phase = .installing
            do {
                if FileManager.default.fileExists(atPath: venvDir.path) {
                    try? FileManager.default.removeItem(at: venvDir)
                }
                try await installVenv()
                try? bundledVersion.write(to: appSupportDir.appendingPathComponent("installed_version.txt"), atomically: true, encoding: .utf8)
            } catch {
                phase = .failed("Installation failed: \(error.localizedDescription)")
                return
            }
        }

        phase = .starting
        do {
            try await ensureOpencodeInstalled()
            let needsUserConfirm = await deployObsidianPlugin()
            try launchProcess()
            if needsUserConfirm { } else {
                // Wait for the backend to be actually responsive before setting .ready
                logger.info("Waiting for health check...")
                try await Task.sleep(nanoseconds: 6_000_000_000) // 6s initial delay for Python startup
                let start = Date()
                var ready = false
                while Date().timeIntervalSince(start) < 30 { // 30s timeout after initial delay
                    if await isBackendResponsive() {
                        ready = true
                        break
                    }
                    try await Task.sleep(nanoseconds: 500_000_000) // 500ms
                }
                if ready {
                    logger.info("Backend is ready and healthy.")
                    obsidianPollTask?.cancel()
                    obsidianPollTask = nil
                    phase = .ready
                    switch await checkObsidian() {
                    case .ready:
                        obsidianWarning = nil
                    case .unreachable:
                        obsidianWarning = "Obsidian is not reachable. Open Obsidian with the Vector Search plugin enabled."
                        obsidianPollTask = Task { await self.pollUntilObsidianReady() }
                    case .versionMismatch(let msg):
                        obsidianWarning = msg
                        obsidianPollTask = Task { await self.pollUntilObsidianReady() }
                    }
                } else {
                    phase = .failed("Backend started but health check failed (timeout).")
                }
            }
        } catch {
            phase = .failed("Launch failed: \(error.localizedDescription)")
        }
    }

    private func isBackendResponsive() async -> Bool {
        let url = URL(string: "http://localhost:51363/health")!
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 1.0
        let session = URLSession(configuration: .ephemeral)
        do {
            let (_, response) = try await session.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    private enum ObsidianStatus {
        case ready
        case unreachable
        case versionMismatch(String)
    }

    private func checkObsidian() async -> ObsidianStatus {
        let url = URL(string: "http://localhost:51362/health")!
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 1.0
        let session = URLSession(configuration: .ephemeral)
        do {
            let (data, response) = try await session.data(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 200 else { return .unreachable }
            if let bundledVersion = getBundledPluginVersion(),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let runningVersion = json["version"] as? String,
               runningVersion.compare(bundledVersion, options: .numeric) == .orderedAscending {
                return .versionMismatch("Plugin version mismatch: Obsidian is running \(runningVersion) but \(bundledVersion) is required. Reload the Vector Search plugin in Obsidian.")
            }
            return .ready
        } catch {
            return .unreachable
        }
    }

    private func pollUntilObsidianReady() async {
        logger.info("Starting Obsidian poll loop")
        while !Task.isCancelled {
            do {
                try await Task.sleep(nanoseconds: 2_000_000_000)
            } catch {
                logger.info("Obsidian poll cancelled during sleep")
                return
            }
            logger.debug("Obsidian poll checking...")
            switch await checkObsidian() {
            case .ready:
                obsidianWarning = nil
                logger.info("Obsidian became available")
                return
            case .unreachable:
                if obsidianWarning == nil {
                    obsidianWarning = "Obsidian is not reachable. Open Obsidian with the Vector Search plugin enabled."
                }
            case .versionMismatch(let msg):
                obsidianWarning = msg
            }
        }
        logger.info("Obsidian poll loop exited (cancelled)")
    }

    private func getBundledPluginVersion() -> String? {
        guard let url = Bundle.main.url(forResource: "manifest", withExtension: "json", subdirectory: "ObsidianPlugin"),
              let data = try? Data(contentsOf: url),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let version = json["version"] as? String else { return nil }
        return version
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

    // MARK: - Obsidian plugin deployment

    private func obsidianPluginDir() -> URL? {
        guard let vaultPath = UserDefaults.standard.string(forKey: "obsidianDir"),
              !vaultPath.isEmpty else { return nil }
        return URL(fileURLWithPath: vaultPath)
            .appendingPathComponent(".obsidian/plugins/obsidian-vector-search")
    }

    private func readManifestVersion(at url: URL) -> String? {
        guard let data = try? Data(contentsOf: url),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let version = json["version"] as? String else { return nil }
        return version
    }

    /// Checks if the bundled plugin differs from the installed one.
    /// If versions differ, sets phase to needsPluginUpdate and returns true.
    /// If not installed at all, copies silently and returns false.
    private func deployObsidianPlugin() async -> Bool {
        guard let pluginDir = obsidianPluginDir() else { return false }
        guard let bundledManifestUrl = Bundle.main.url(forResource: "manifest", withExtension: "json", subdirectory: "ObsidianPlugin"),
              let mainJsUrl = Bundle.main.url(forResource: "main", withExtension: "js", subdirectory: "ObsidianPlugin") else {
            return false
        }

        let bundledVersion = readManifestVersion(at: bundledManifestUrl)
        let installedManifestUrl = pluginDir.appendingPathComponent("manifest.json")
        let installedVersion = readManifestVersion(at: installedManifestUrl)
        let alreadyInstalled = FileManager.default.fileExists(atPath: installedManifestUrl.path)

        guard bundledVersion != installedVersion else { return false }

        if alreadyInstalled {
            phase = .needsPluginUpdate(installedVersion ?? "?", bundledVersion ?? "?")
            return true
        }

        // First install — copy silently
        do {
            try FileManager.default.createDirectory(at: pluginDir, withIntermediateDirectories: true)
            let destMain = pluginDir.appendingPathComponent("main.js")
            let destManifest = pluginDir.appendingPathComponent("manifest.json")
            if FileManager.default.fileExists(atPath: destMain.path) { try FileManager.default.removeItem(at: destMain) }
            if FileManager.default.fileExists(atPath: destManifest.path) { try FileManager.default.removeItem(at: destManifest) }
            try FileManager.default.copyItem(at: mainJsUrl, to: destMain)
            try FileManager.default.copyItem(at: bundledManifestUrl, to: destManifest)
            writeDragonglassConfig(to: pluginDir)
        } catch {
            print("[BackendManager] Plugin deploy failed: \(error)")
        }
        return false
    }

    func applyPluginUpdate() {
        guard let pluginDir = obsidianPluginDir(),
              let bundledManifestUrl = Bundle.main.url(forResource: "manifest", withExtension: "json", subdirectory: "ObsidianPlugin"),
              let mainJsUrl = Bundle.main.url(forResource: "main", withExtension: "js", subdirectory: "ObsidianPlugin") else {
            return
        }
        do {
            try FileManager.default.createDirectory(at: pluginDir, withIntermediateDirectories: true)
            let destMain = pluginDir.appendingPathComponent("main.js")
            let destManifest = pluginDir.appendingPathComponent("manifest.json")
            if FileManager.default.fileExists(atPath: destMain.path) { try FileManager.default.removeItem(at: destMain) }
            if FileManager.default.fileExists(atPath: destManifest.path) { try FileManager.default.removeItem(at: destManifest) }
            try FileManager.default.copyItem(at: mainJsUrl, to: destMain)
            try FileManager.default.copyItem(at: bundledManifestUrl, to: destManifest)
            writeDragonglassConfig(to: pluginDir)
            phase = .needsPluginReload
        } catch {
            print("[BackendManager] Plugin update failed: \(error)")
        }
    }

    private func writeDragonglassConfig(to pluginDir: URL) {
        let configPath = pluginDir.appendingPathComponent("dragonglass.json")
        let config: [String: Any] = ["port": 51362]
        if let data = try? JSONSerialization.data(withJSONObject: config) {
            try? data.write(to: configPath)
        }
    }

    // MARK: - Kill existing backend

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
            try? await Task.sleep(nanoseconds: 500_000_000)

            // 2. Fallback to hard kill for any stragglers
            Self.killProcesses(onPort: 51363, label: "backend", matcher: .backend)
            Self.killProcesses(onPort: 51364, label: "mcp", matcher: .mcp)
        }.value
    }

    private enum ProcessMatcher {
        case backend
        case mcp
    }

    nonisolated private static func killProcesses(
        onPort port: Int,
        label: String,
        matcher: ProcessMatcher
    ) {
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
            print("[BackendManager] Killing orphaned \(label) process PID \(target.pid) (\(target.command)) on port \(port)")
            let killProcess = Process()
            killProcess.executableURL = URL(fileURLWithPath: "/bin/kill")
            killProcess.arguments = ["-9", "\(target.pid)"]
            try? killProcess.run()
            killProcess.waitUntilExit()
        }
    }

    private struct LsofProcessEntry {
        let pid: Int
        let command: String
        let processName: String
    }

    nonisolated private static func parseLsofProcessEntries(_ output: String) -> [LsofProcessEntry] {
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
                    entries.append(
                        LsofProcessEntry(
                            pid: pid,
                            command: currentCommand,
                            processName: currentCommand.lowercased()
                        )
                    )
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
            entries.append(
                LsofProcessEntry(
                    pid: pid,
                    command: currentCommand,
                    processName: currentCommand.lowercased()
                )
            )
        }
        return entries
    }

    nonisolated private static func isExpectedProcess(_ process: LsofProcessEntry, matcher: ProcessMatcher) -> Bool {
        switch matcher {
        case .backend:
            return process.processName.contains("dragonglass") || process.processName.contains("python")
        case .mcp:
            return process.processName.contains("python") || process.processName.contains("uvicorn") || process.processName.contains("dragonglass")
        }
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

        // 1.5 Ensure uv is available in the app-managed environment.
        if !FileManager.default.isExecutableFile(atPath: uvPath.path) {
            let uvInstallProcess = Process()
            uvInstallProcess.executableURL = pythonPath
            uvInstallProcess.arguments = ["-m", "pip", "install", "uv"]
            do {
                try await uvInstallProcess.runAsync()
            } catch {
                print("[BackendManager] uv install failed, falling back to pip: \(error)")
            }
        }

        // 2. Install wheel from bundle
        guard let wheelDir = Bundle.main.url(forResource: "wheels", withExtension: nil) else {
            throw NSError(domain: "BackendManager", code: 1, userInfo: [NSLocalizedDescriptionKey: "Wheels not found in bundle"])
        }

        print("[BackendManager] Installing wheels from \(wheelDir.path)...")
        if FileManager.default.isExecutableFile(atPath: uvPath.path) {
            let uvInstallProcess = Process()
            uvInstallProcess.executableURL = uvPath
            uvInstallProcess.arguments = [
                "pip", "install",
                "--python", pythonPath.path,
                "--no-index",
                "--find-links", wheelDir.path,
                "dragonglass"
            ]
            do {
                try await uvInstallProcess.runAsync()
                return
            } catch {
                print("[BackendManager] uv package install failed, falling back to pip: \(error)")
            }
        }

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

    private func bundledOpencodePackageData() -> Data? {
        guard let url = Bundle.main.url(forResource: "opencode_package", withExtension: "json"),
              let data = try? Data(contentsOf: url) else {
            return nil
        }
        return data
    }

    private func bundledOpencodeCliVersion() -> String? {
        guard let data = bundledOpencodePackageData(),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let deps = json["dependencies"] as? [String: String],
              let version = deps["opencode-ai"] else {
            return nil
        }
        return version
    }

    private func installedOpencodeCliVersion() -> String? {
        guard let data = try? Data(contentsOf: opencodeCliPackagePath),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let version = json["version"] as? String else {
            return nil
        }
        return version
    }

    private func findNpm() -> String? {
        let candidates = [
            "/opt/homebrew/bin/npm",
            "/usr/local/bin/npm",
            "/usr/bin/npm",
            "npm"
        ]
        for candidate in candidates {
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
            process.arguments = ["which", candidate]
            let pipe = Pipe()
            process.standardOutput = pipe
            try? process.run()
            process.waitUntilExit()
            if process.terminationStatus == 0 {
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                if let output = String(data: data, encoding: .utf8) {
                    let trimmed = output.trimmingCharacters(in: .whitespacesAndNewlines)
                    if !trimmed.isEmpty {
                        return trimmed
                    }
                }
            }
        }
        return nil
    }

    private func ensureOpencodeInstalled() async throws {
        guard let bundledPackageData = bundledOpencodePackageData() else {
            print("[BackendManager] Missing bundled opencode_package.json, skipping OpenCode install")
            return
        }

        let localPackage = opencodeInstallDir.appendingPathComponent("package.json")
        let localPackageData = try? Data(contentsOf: localPackage)
        let packageChanged = localPackageData != bundledPackageData

        let desiredCliVersion = bundledOpencodeCliVersion()
        let installedCliVersion = installedOpencodeCliVersion()
        let cliVersionChanged = desiredCliVersion != installedCliVersion

        let needsInstall = !FileManager.default.isExecutableFile(atPath: opencodeBinPath.path)
            || packageChanged
            || cliVersionChanged
        if !needsInstall {
            return
        }

        guard let npmPath = findNpm() else {
            throw NSError(
                domain: "BackendManager",
                code: 2,
                userInfo: [
                    NSLocalizedDescriptionKey: "npm is required to install OpenCode. Install Node.js (npm) and retry."
                ]
            )
        }

        try FileManager.default.createDirectory(at: opencodeInstallDir, withIntermediateDirectories: true)
        if FileManager.default.fileExists(atPath: localPackage.path) {
            try? FileManager.default.removeItem(at: localPackage)
        }
        try bundledPackageData.write(to: localPackage)

        var env = ProcessInfo.processInfo.environment
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + (env["PATH"] ?? "")

        print("[BackendManager] Installing OpenCode CLI with npm using \(npmPath)...")
        let installProcess = Process()
        installProcess.executableURL = URL(fileURLWithPath: npmPath)
        installProcess.arguments = ["install", "--omit=dev", "--no-audit", "--no-fund"]
        installProcess.currentDirectoryURL = opencodeInstallDir
        installProcess.environment = env
        try await installProcess.runAsync()

        guard FileManager.default.isExecutableFile(atPath: opencodeBinPath.path) else {
            throw NSError(
                domain: "BackendManager",
                code: 4,
                userInfo: [NSLocalizedDescriptionKey: "OpenCode CLI install completed but binary was not found."]
            )
        }

        if let desiredCliVersion,
           let installedCliVersion,
           desiredCliVersion != installedCliVersion {
            throw NSError(
                domain: "BackendManager",
                code: 5,
                userInfo: [
                    NSLocalizedDescriptionKey: "OpenCode CLI version mismatch: expected \(desiredCliVersion), found \(installedCliVersion)."
                ]
            )
        }

    }

    private func launchProcess() throws {
        let p = Process()
        p.executableURL = dragonglassPath
        p.arguments = ["serve"]

        var env = ProcessInfo.processInfo.environment
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + (env["PATH"] ?? "")
        env["OPENCODE_CONFIG"] = opencodeConfigPath.path
        env["OPENCODE_BIN"] = opencodeBinPath.path
        p.environment = env

        try FileManager.default.createDirectory(
            at: opencodeConfigPath.deletingLastPathComponent(),
            withIntermediateDirectories: true,
            attributes: nil
        )

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
            Task { @MainActor [weak self] in
                guard let self else { return }
                if self.process == process {
                    self.phase = .failed("Backend exited with code \(process.terminationStatus)")
                }
            }
        }

        self.process = p
        try p.run()
    }

    func cancelObsidianPoll() {
        obsidianPollTask?.cancel()
        obsidianPollTask = nil
    }

    deinit {
        obsidianPollTask?.cancel()
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
