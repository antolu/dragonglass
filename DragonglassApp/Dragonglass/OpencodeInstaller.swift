import Foundation
import OSLog

private let logger = Logger(subsystem: subsystem, category: "BackendManager")

func bundledOpencodePackageData() -> Data? {
    guard let url = Bundle.main.url(forResource: "opencode_package", withExtension: "json"),
          let data = try? Data(contentsOf: url) else {
        return nil
    }
    return data
}

func bundledOpencodeCliVersion() -> String? {
    guard let data = bundledOpencodePackageData(),
          let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let deps = json["dependencies"] as? [String: String],
          let version = deps["opencode-ai"] else {
        return nil
    }
    return version
}

func installedOpencodeCliVersion(paths: BackendPaths) -> String? {
    guard let data = try? Data(contentsOf: paths.opencodeCliPackagePath),
          let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let version = json["version"] as? String else {
        return nil
    }
    return version
}

func findNpm() -> String? {
    let homeDir = FileManager.default.homeDirectoryForCurrentUser

    let extraPaths = [
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        homeDir.appendingPathComponent(".volta/bin").path,
        homeDir.appendingPathComponent(".fnm").path
    ]
    let augmentedPath = (extraPaths + (ProcessInfo.processInfo.environment["PATH"] ?? "")
        .components(separatedBy: ":")).joined(separator: ":")

    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/which")
    process.arguments = ["-a", "npm"]
    process.environment = ["PATH": augmentedPath]
    let pipe = Pipe()
    process.standardOutput = pipe
    try? process.run()
    process.waitUntilExit()

    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    if let output = String(data: data, encoding: .utf8) {
        let found = output.components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        if let first = found.first { return first }
    }

    var hardcoded = [
        "/opt/homebrew/bin/npm",
        "/usr/local/bin/npm",
        "/usr/bin/npm",
        homeDir.appendingPathComponent(".volta/bin/npm").path
    ]
    let nvmBase = homeDir.appendingPathComponent(".nvm/versions/node")
    if let versions = try? FileManager.default.contentsOfDirectory(atPath: nvmBase.path).sorted() {
        for v in versions.reversed() {
            hardcoded.insert(nvmBase.appendingPathComponent("\(v)/bin/npm").path, at: 0)
        }
    }

    for candidate in hardcoded {
        if FileManager.default.fileExists(atPath: candidate) { return candidate }
    }
    return nil
}

func ensureOpencodeInstalled(paths: BackendPaths) async throws {
    guard let bundledPackageData = bundledOpencodePackageData() else {
        logger.warning("Missing bundled opencode_package.json, skipping OpenCode install")
        return
    }

    let localPackage = paths.opencodeInstallDir.appendingPathComponent("package.json")
    let localPackageData = try? Data(contentsOf: localPackage)
    let packageChanged = localPackageData != bundledPackageData

    let desiredCliVersion = bundledOpencodeCliVersion()
    let installedCliVersion = installedOpencodeCliVersion(paths: paths)
    let cliVersionChanged = desiredCliVersion != installedCliVersion

    let needsInstall = !FileManager.default.isExecutableFile(atPath: paths.opencodeBinPath.path)
        || packageChanged
        || cliVersionChanged
    if !needsInstall { return }

    guard let npmPath = findNpm() else {
        throw NSError(
            domain: "BackendManager",
            code: 2,
            userInfo: [NSLocalizedDescriptionKey: "npm is required to install OpenCode. Install Node.js (npm) and retry."]
        )
    }

    try FileManager.default.createDirectory(at: paths.opencodeInstallDir, withIntermediateDirectories: true)
    if FileManager.default.fileExists(atPath: localPackage.path) {
        try? FileManager.default.removeItem(at: localPackage)
    }
    try bundledPackageData.write(to: localPackage)

    var env = ProcessInfo.processInfo.environment
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + (env["PATH"] ?? "")

    logger.info("Installing OpenCode CLI with npm path=\(npmPath, privacy: .public)")
    let installProcess = Process()
    installProcess.executableURL = URL(fileURLWithPath: npmPath)
    installProcess.arguments = ["install", "--omit=dev", "--no-audit", "--no-fund"]
    installProcess.currentDirectoryURL = paths.opencodeInstallDir
    installProcess.environment = env
    try await installProcess.runAsync()

    guard FileManager.default.isExecutableFile(atPath: paths.opencodeBinPath.path) else {
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
            userInfo: [NSLocalizedDescriptionKey: "OpenCode CLI version mismatch: expected \(desiredCliVersion), found \(installedCliVersion)."]
        )
    }
}
