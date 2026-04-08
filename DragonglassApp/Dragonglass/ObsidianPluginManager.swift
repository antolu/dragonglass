import Foundation
import OSLog

private let logger = Logger(subsystem: subsystem, category: "BackendManager")

func getBundledPluginVersion() -> String? {
    guard let url = Bundle.main.url(forResource: "manifest", withExtension: "json", subdirectory: "ObsidianPlugin"),
          let data = try? Data(contentsOf: url),
          let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let version = json["version"] as? String else { return nil }
    return version
}

func obsidianPluginDir() -> URL? {
    guard let vaultPath = UserDefaults.standard.string(forKey: "obsidianDir"),
          !vaultPath.isEmpty else { return nil }
    return URL(fileURLWithPath: vaultPath)
        .appendingPathComponent(".obsidian/plugins/obsidian-vector-search")
}

func readManifestVersion(at url: URL) -> String? {
    guard let data = try? Data(contentsOf: url),
          let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let version = json["version"] as? String else { return nil }
    return version
}

func writeDragonglassConfig(to pluginDir: URL) {
    let configPath = pluginDir.appendingPathComponent("dragonglass.json")
    let config: [String: Any] = ["port": BackendPaths.obsidianPort]
    if let data = try? JSONSerialization.data(withJSONObject: config) {
        try? data.write(to: configPath)
    }
}

enum PluginDeployResult {
    case noChange
    case needsUpdate(installed: String, bundled: String)
    case deployed
}

/// Checks if the bundled plugin differs from the installed one.
/// Returns .needsUpdate if already installed with a different version,
/// .deployed if silently installed for the first time, .noChange otherwise.
func deployObsidianPlugin() async -> PluginDeployResult {
    guard let pluginDir = obsidianPluginDir() else { return .noChange }
    guard let bundledManifestUrl = Bundle.main.url(forResource: "manifest", withExtension: "json", subdirectory: "ObsidianPlugin"),
          let mainJsUrl = Bundle.main.url(forResource: "main", withExtension: "js", subdirectory: "ObsidianPlugin") else {
        return .noChange
    }

    let bundledVersion = readManifestVersion(at: bundledManifestUrl)
    let installedManifestUrl = pluginDir.appendingPathComponent("manifest.json")
    let installedVersion = readManifestVersion(at: installedManifestUrl)
    let alreadyInstalled = FileManager.default.fileExists(atPath: installedManifestUrl.path)

    guard bundledVersion != installedVersion else { return .noChange }

    if alreadyInstalled {
        return .needsUpdate(installed: installedVersion ?? "?", bundled: bundledVersion ?? "?")
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
    } catch {
        logger.error("Plugin deploy failed error=\(error.localizedDescription, privacy: .public)")
    }
    return .deployed
}

func copyPluginUpdate() -> Bool {
    guard let pluginDir = obsidianPluginDir(),
          let bundledManifestUrl = Bundle.main.url(forResource: "manifest", withExtension: "json", subdirectory: "ObsidianPlugin"),
          let mainJsUrl = Bundle.main.url(forResource: "main", withExtension: "js", subdirectory: "ObsidianPlugin") else {
        return false
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
        return true
    } catch {
        logger.error("Plugin update failed error=\(error.localizedDescription, privacy: .public)")
        return false
    }
}
