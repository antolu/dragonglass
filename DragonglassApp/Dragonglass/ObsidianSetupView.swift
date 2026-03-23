import SwiftUI
import AppKit
import Combine

enum SetupStep {
    case pickVault
    case installPlugin
    case waitForHealth
    case done
}

@MainActor
class ObsidianSetupViewModel: ObservableObject {
    @Published var step: SetupStep = .pickVault
    @Published var vaultPath: String = ""
    @Published var vaultError: String?
    @Published var installError: String?
    @Published var isHealthy = false
    @Published var isPolling = false

    private let pluginId = "obsidian-vector-search"
    private var healthPollTask: Task<Void, Never>?

    var pluginDir: URL? {
        guard !vaultPath.isEmpty else { return nil }
        return URL(fileURLWithPath: vaultPath)
            .appendingPathComponent(".obsidian/plugins/\(pluginId)")
    }

    func pickVault() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.title = "Select your Obsidian vault folder"
        panel.prompt = "Select"

        if panel.runModal() == .OK, let url = panel.url {
            validate(vaultURL: url)
        }
    }

    private func validate(vaultURL: URL) {
        let appJson = vaultURL.appendingPathComponent(".obsidian/app.json")
        guard FileManager.default.fileExists(atPath: appJson.path) else {
            vaultError = "Not a valid Obsidian vault — .obsidian/app.json not found."
            return
        }
        vaultError = nil
        vaultPath = vaultURL.path
        UserDefaults.standard.set(vaultPath, forKey: "obsidianDir")
        step = .installPlugin
    }

    func installPlugin() {
        guard let pluginDir else { return }
        installError = nil

        do {
            try FileManager.default.createDirectory(at: pluginDir, withIntermediateDirectories: true)

            guard let mainJsUrl = Bundle.main.url(forResource: "main", withExtension: "js", subdirectory: "ObsidianPlugin"),
                  let manifestUrl = Bundle.main.url(forResource: "manifest", withExtension: "json", subdirectory: "ObsidianPlugin") else {
                installError = "Bundled plugin files not found. Rebuild the app."
                return
            }

            let destMain = pluginDir.appendingPathComponent("main.js")
            let destManifest = pluginDir.appendingPathComponent("manifest.json")

            if FileManager.default.fileExists(atPath: destMain.path) {
                try FileManager.default.removeItem(at: destMain)
            }
            if FileManager.default.fileExists(atPath: destManifest.path) {
                try FileManager.default.removeItem(at: destManifest)
            }

            try FileManager.default.copyItem(at: mainJsUrl, to: destMain)
            try FileManager.default.copyItem(at: manifestUrl, to: destManifest)

            enablePlugin()
            writeDragonglassConfig()

            step = .waitForHealth
            startHealthPolling()
        } catch {
            installError = "Installation failed: \(error.localizedDescription)"
        }
    }

    private func enablePlugin() {
        guard let vaultURL = pluginDir?.deletingLastPathComponent().deletingLastPathComponent() else { return }
        let communityPluginsPath = vaultURL.appendingPathComponent(".obsidian/community-plugins.json")

        var plugins: [String] = []
        if let data = try? Data(contentsOf: communityPluginsPath),
           let existing = try? JSONDecoder().decode([String].self, from: data) {
            plugins = existing
        }
        if !plugins.contains(pluginId) {
            plugins.append(pluginId)
            if let data = try? JSONEncoder().encode(plugins) {
                try? data.write(to: communityPluginsPath)
            }
        }
    }

    private func writeDragonglassConfig() {
        guard let pluginDir else { return }
        let configPath = pluginDir.appendingPathComponent("dragonglass.json")
        let config = ["port": 51362]
        if let data = try? JSONSerialization.data(withJSONObject: config) {
            try? data.write(to: configPath)
        }
    }

    func startHealthPolling() {
        isPolling = true
        healthPollTask = Task {
            while !isHealthy && !Task.isCancelled {
                await checkHealth()
                if !isHealthy {
                    try? await Task.sleep(nanoseconds: 2_000_000_000)
                }
            }
            isPolling = false
        }
    }

    private func checkHealth() async {
        guard let url = URL(string: "http://127.0.0.1:51362/health") else { return }
        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            if let http = response as? HTTPURLResponse, http.statusCode == 200,
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               json["status"] as? String == "ok" {
                isHealthy = true
            }
        } catch {
            // not yet healthy
        }
    }

    func finish() {
        healthPollTask?.cancel()
        step = .done
    }
}

struct ObsidianSetupView: View {
    @Binding var isPresented: Bool
    var onComplete: ((String) -> Void)? = nil
    @StateObject private var vm = ObsidianSetupViewModel()

    var body: some View {
        VStack(spacing: 24) {
            Text("Obsidian Setup")
                .font(.title2)
                .fontWeight(.semibold)

            switch vm.step {
            case .pickVault:
                pickVaultStep
            case .installPlugin:
                installPluginStep
            case .waitForHealth:
                waitForHealthStep
            case .done:
                EmptyView()
                    .onAppear { isPresented = false }
            }
        }
        .padding(32)
        .frame(width: 420)
    }

    private var pickVaultStep: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Select your Obsidian vault folder. Dragonglass will validate the directory and install its companion plugin there.")
                .foregroundColor(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            if let error = vm.vaultError {
                Label(error, systemImage: "exclamationmark.triangle")
                    .foregroundColor(.red)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack {
                Spacer()
                Button("Select Vault Folder…") {
                    vm.pickVault()
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    private var installPluginStep: some View {
        VStack(alignment: .leading, spacing: 16) {
            Label("Vault: \(vm.vaultPath)", systemImage: "checkmark.circle.fill")
                .foregroundColor(.green)
                .lineLimit(1)
                .truncationMode(.middle)

            Text("Dragonglass will install the Vector Search plugin into your vault and add it to community-plugins.json.")
                .foregroundColor(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            if let error = vm.installError {
                Label(error, systemImage: "exclamationmark.triangle")
                    .foregroundColor(.red)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack {
                Button("Back") { vm.step = .pickVault }
                    .buttonStyle(.plain)
                    .foregroundColor(.secondary)
                Spacer()
                Button("Install Plugin") {
                    vm.installPlugin()
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    private var waitForHealthStep: some View {
        VStack(alignment: .leading, spacing: 16) {
            Label("Plugin installed.", systemImage: "checkmark.circle.fill")
                .foregroundColor(.green)

            Text("Enable the **Vector Search** plugin in Obsidian → Settings → Community plugins, then click Enable. Dragonglass is waiting for the plugin to respond…")
                .foregroundColor(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            HStack(spacing: 8) {
                if vm.isHealthy {
                    Label("Plugin is running", systemImage: "checkmark.circle.fill")
                        .foregroundColor(.green)
                } else {
                    ProgressView()
                        .scaleEffect(0.7)
                    Text("Waiting for plugin...")
                        .foregroundColor(.secondary)
                }
                Spacer()
                Button("Continue") {
                    vm.finish()
                    onComplete?(vm.vaultPath)
                    isPresented = false
                }
                .buttonStyle(.borderedProminent)
                .disabled(!vm.isHealthy)
            }
        }
    }
}
