import Foundation
import Combine
import OSLog

private let logger = Logger(subsystem: subsystem, category: "BackendManager")

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

struct BackendPaths {
    let appSupportDir: URL
    var venvDir: URL { appSupportDir.appendingPathComponent("venv") }
    var pythonPath: URL { venvDir.appendingPathComponent("bin/python3") }
    var uvPath: URL { venvDir.appendingPathComponent("bin/uv") }
    var dragonglassPath: URL { venvDir.appendingPathComponent("bin/dragonglass") }
    var opencodeInstallDir: URL { appSupportDir.appendingPathComponent("opencode") }
    var opencodeBinPath: URL { opencodeInstallDir.appendingPathComponent("node_modules/.bin/opencode") }
    var opencodeCliPackagePath: URL { opencodeInstallDir.appendingPathComponent("node_modules/opencode-ai/package.json") }
    var opencodeConfigPath: URL { appSupportDir.appendingPathComponent("config/opencode.json") }

    /// Port the dragonglass Python server listens on.
    static let backendPort = 51363
    /// Port the dragonglass MCP server listens on.
    static let mcpPort = 51364
    /// Port the Obsidian Vector Search plugin listens on.
    static let obsidianPort = 51362
    /// WebSocket endpoint for the dragonglass Python server.
    static var backendWebSocketURL: URL { URL(string: "ws://localhost:\(backendPort)")! }
    static var backendHealthURL: URL { URL(string: "http://localhost:\(backendPort)/health")! }
    static var obsidianHealthURL: URL { URL(string: "http://localhost:\(obsidianPort)/health")! }

    static let `default`: BackendPaths = {
        let paths = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
        return BackendPaths(appSupportDir: paths[0].appendingPathComponent("dragonglass"))
    }()
}

/// Timing constants for backend startup, health checks, and polling.
struct BackendTimings {
    /// Initial wait after launching the Python process before polling /health.
    /// Python startup + uvicorn bind typically takes 4–6 s.
    static let pythonStartupDelay: Duration = .seconds(6)
    /// Interval between /health retries during the startup window.
    static let healthCheckInterval: Duration = .milliseconds(500)
    /// Total time allowed for the backend to become healthy after the initial delay.
    static let healthCheckTimeout: TimeInterval = 30
    /// Per-request timeout for individual /health HTTP calls.
    static let healthRequestTimeout: TimeInterval = 1
    /// Grace period between sending `dragonglass stop` and force-killing leftover processes.
    static let gracefulShutdownDelay: Duration = .milliseconds(500)
    /// Interval between Obsidian availability checks while waiting for the plugin to come up.
    static let obsidianPollInterval: Duration = .seconds(2)
}

@MainActor
class BackendManager: ObservableObject {
    @Published var phase: BackendPhase = .starting
    @Published var obsidianWarning: String?
    private var process: Process?
    private var obsidianPollTask: Task<Void, Never>?

    private let paths = BackendPaths.default

    init() {
        Task {
            await startBackend()
        }
    }

    func startBackend() async {
        logger.info("startBackend begin")
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

        let needsInstall = !FileManager.default.fileExists(atPath: paths.dragonglassPath.path)
            || bundledVersion != installedVersion

        if needsInstall {
            logger.info("startBackend install required bundled=\(bundledVersion, privacy: .public) installed=\((installedVersion ?? "none"), privacy: .public)")
            phase = .installing
            do {
                if FileManager.default.fileExists(atPath: paths.venvDir.path) {
                    try? FileManager.default.removeItem(at: paths.venvDir)
                }
                try await installVenv(paths: paths)
                try? bundledVersion.write(to: paths.appSupportDir.appendingPathComponent("installed_version.txt"), atomically: true, encoding: .utf8)
            } catch {
                phase = .failed("Installation failed: \(error.localizedDescription)")
                return
            }
        }

        phase = .starting
        do {
            try await ensureOpencodeInstalled(paths: paths)
            let deployResult = await deployObsidianPlugin()
            if case .needsUpdate(let installed, let bundled) = deployResult {
                phase = .needsPluginUpdate(installed, bundled)
            }
            try launchProcess()
            if case .needsUpdate = deployResult { } else {
                logger.info("Waiting for health check...")
                try await Task.sleep(for: BackendTimings.pythonStartupDelay)
                let start = Date()
                var ready = false
                while Date().timeIntervalSince(start) < BackendTimings.healthCheckTimeout {
                    if await isBackendResponsive() {
                        ready = true
                        break
                    }
                    try await Task.sleep(for: BackendTimings.healthCheckInterval)
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
                    logger.error("backend health check timed out")
                    phase = .failed("Backend started but health check failed (timeout).")
                }
            }
        } catch {
            logger.error("startBackend failed error=\(error.localizedDescription, privacy: .public)")
            phase = .failed("Launch failed: \(error.localizedDescription)")
        }
    }

    func applyPluginUpdate() {
        if copyPluginUpdate() {
            phase = .needsPluginReload
        }
    }

    private func isBackendResponsive() async -> Bool {
        let url = BackendPaths.backendHealthURL
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = BackendTimings.healthRequestTimeout
        let session = URLSession(configuration: .ephemeral)
        do {
            let (_, response) = try await session.data(for: request)
            let healthy = (response as? HTTPURLResponse)?.statusCode == 200
            logger.debug("isBackendResponsive healthy=\(healthy)")
            return healthy
        } catch {
            logger.debug("isBackendResponsive request failed")
            return false
        }
    }

    private enum ObsidianStatus {
        case ready
        case unreachable
        case versionMismatch(String)
    }

    private func checkObsidian() async -> ObsidianStatus {
        let url = BackendPaths.obsidianHealthURL
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = BackendTimings.healthRequestTimeout
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
                try await Task.sleep(for: BackendTimings.obsidianPollInterval)
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

    private func getBundledVersion() -> String? {
        guard let url = Bundle.main.url(forResource: "version", withExtension: "txt"),
              let version = try? String(contentsOf: url, encoding: .utf8) else {
            return nil
        }
        return version.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func getInstalledVersion() -> String? {
        let url = paths.appSupportDir.appendingPathComponent("installed_version.txt")
        guard let version = try? String(contentsOf: url, encoding: .utf8) else {
            return nil
        }
        return version.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func findAndKillExistingBackend() async {
        let dragonglassPath = paths.dragonglassPath
        await Task.detached {
            let stopProcess = Process()
            stopProcess.executableURL = dragonglassPath
            stopProcess.arguments = ["stop"]
            try? stopProcess.run()
            stopProcess.waitUntilExit()

            try? await Task.sleep(for: BackendTimings.gracefulShutdownDelay)

            killProcesses(onPort: BackendPaths.backendPort, label: "backend", matcher: .backend)
            killProcesses(onPort: BackendPaths.mcpPort, label: "mcp", matcher: .mcp)
        }.value
    }

    private func launchProcess() throws {
        let p = Process()
        p.executableURL = paths.dragonglassPath
        p.arguments = ["serve"]

        var env = ProcessInfo.processInfo.environment
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + (env["PATH"] ?? "")
        env["OPENCODE_CONFIG"] = paths.opencodeConfigPath.path
        env["OPENCODE_BIN"] = paths.opencodeBinPath.path
        p.environment = env

        try FileManager.default.createDirectory(
            at: paths.opencodeConfigPath.deletingLastPathComponent(),
            withIntermediateDirectories: true,
            attributes: nil
        )

        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = pipe

        let handle = pipe.fileHandleForReading
        handle.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty, let str = String(data: data, encoding: .utf8) {
                logger.debug("[Backend] \(str, privacy: .public)")
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
