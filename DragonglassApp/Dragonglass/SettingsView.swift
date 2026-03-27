import SwiftUI
import AppKit

struct SettingsView: View {
    @Binding var isPresented: Bool
    @EnvironmentObject var client: AgentClient

    @State private var config: DragonglassConfig?
    @State private var baselineConfig: DragonglassConfig?
    @State private var isLoading = true
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var showError = false
    @State private var saveMessage: String?
    @State private var newEnvKey = ""
    @State private var newEnvValue = ""
    @State private var envFilter = ""
    @AppStorage("closePopoverOnFocusLoss") private var closePopoverOnFocusLoss = false

    var body: some View {
        VStack(spacing: 0) {
            header

            if isLoading {
                Spacer()
                ProgressView()
                Spacer()
            } else if let config = Binding($config) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        vaultSection(config)
                        modelSection(config)
                        backendSection(config)
                        permissionsSection(config)
                        advancedSection(config)
                    }
                    .padding(.horizontal)
                    .padding(.top, 10)
                    .padding(.bottom, 12)
                }
            } else {
                Spacer()
            }

            Spacer(minLength: 0)
            footer
        }
        .frame(width: 380, height: 470)
        .alert("Error", isPresented: $showError, presenting: errorMessage) { _ in
            Button("OK") { showError = false }
        } message: { message in
            Text(message)
        }
        .onAppear {
            loadConfig()
        }
    }

    private var header: some View {
        HStack {
            Text("Settings")
                .font(.headline)
            Spacer()
            if let saveMessage {
                Text(saveMessage)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            Button(action: saveConfig) {
                HStack(spacing: 4) {
                    if isSaving {
                        ProgressView()
                            .scaleEffect(0.7)
                            .frame(width: 10, height: 10)
                    } else {
                        Image(systemName: "checkmark")
                    }
                    Text(isSaving ? "Saving" : "Save")
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .foregroundColor(.accentColor)
            }
            .buttonStyle(.plain)
            .focusable(false)
            .disabled(isSaving || !hasUnsavedChanges)
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color(NSColor.windowBackgroundColor))
    }

    private var footer: some View {
        HStack {
            Text(hasUnsavedChanges ? "Unsaved changes" : "All changes saved")
                .font(.caption)
                .foregroundColor(.secondary)
            Spacer()
            Button("Quit") {
                NSApplication.shared.terminate(nil)
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color(NSColor.windowBackgroundColor))
    }

    @ViewBuilder
    private func vaultSection(_ config: Binding<DragonglassConfig>) -> some View {
        settingsSection("Obsidian Vault") {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 8) {
                    Text(config.obsidianDir.wrappedValue.isEmpty ? "Not configured" : "Configured")
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(
                            config.obsidianDir.wrappedValue.isEmpty
                                ? Color.orange.opacity(0.2)
                                : Color.green.opacity(0.2)
                        )
                        .clipShape(Capsule())
                    Spacer()
                    Button("Change…") {
                        SetupWindowController.shared.show { vaultPath in
                            guard var current = self.config else { return }
                            Task {
                                current.obsidianDir = vaultPath
                                do {
                                    try await self.client.setConfig(current)
                                    await MainActor.run {
                                        self.config = current
                                        self.baselineConfig = current
                                        self.saveMessage = "Saved"
                                    }
                                } catch {
                                    await MainActor.run {
                                        self.errorMessage =
                                            "Failed to save vault path: \(error.localizedDescription)"
                                        self.showError = true
                                    }
                                }
                            }
                        }
                    }
                    .buttonStyle(.plain)
                    .foregroundColor(.accentColor)
                }

                HStack(spacing: 6) {
                    Text(config.obsidianDir.wrappedValue.isEmpty ? "Not configured" : config.obsidianDir.wrappedValue)
                        .font(.system(.caption, design: .monospaced))
                        .foregroundColor(config.obsidianDir.wrappedValue.isEmpty ? .secondary : .primary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                    Spacer()
                    if !config.obsidianDir.wrappedValue.isEmpty {
                        Button {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(config.obsidianDir.wrappedValue, forType: .string)
                        } label: {
                            Image(systemName: "doc.on.doc")
                        }
                        .buttonStyle(.plain)
                        .help("Copy vault path")
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func modelSection(_ config: Binding<DragonglassConfig>) -> some View {
        settingsSection("Model") {
            VStack(alignment: .leading, spacing: 8) {
                Text("Default Model")
                    .font(.caption)
                    .foregroundColor(.secondary)
                TextField("Default Model", text: config.llmModel)
            }
        }
    }

    @ViewBuilder
    private func backendSection(_ config: Binding<DragonglassConfig>) -> some View {
        settingsSection("LLM Backend") {
            VStack(alignment: .leading, spacing: 8) {
                let opencodeAvailable = config.opencodeAvailable.wrappedValue ?? true
                let opencodeDisabledReason = config.opencodeDisabledReason.wrappedValue

                Picker("Backend", selection: config.llmBackend) {
                    Text("LiteLLM").tag("litellm")
                    Text("OpenCode")
                        .tag("opencode")
                        .disabled(!opencodeAvailable)
                        .help(opencodeDisabledReason ?? "OpenCode is unavailable")
                }
                .pickerStyle(.segmented)
                .onChange(of: config.llmBackend.wrappedValue) { newBackend in
                    config.selectedModel.wrappedValue = ""
                    client.setBackend(newBackend)
                }

                if !opencodeAvailable {
                    Text(opencodeDisabledReason ?? "OpenCode is unavailable")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                if config.llmBackend.wrappedValue == "opencode" {
                    Toggle("Spawn Managed Server", isOn: config.spawnOpencode)
                }
            }
        }
    }

    @ViewBuilder
    private func permissionsSection(_ config: Binding<DragonglassConfig>) -> some View {
        settingsSection("Permissions") {
            VStack(alignment: .leading, spacing: 8) {
                Toggle("Auto-allow Edits", isOn: config.autoAllowEdit)
                Toggle("Auto-allow Create", isOn: config.autoAllowCreate)
                Toggle("Auto-allow Delete", isOn: config.autoAllowDelete)
            }
        }
    }

    @ViewBuilder
    private func environmentSection(_ config: Binding<DragonglassConfig>) -> some View {
        settingsSection("Environment Variables") {
            let envVars = config.envVars.wrappedValue ?? [:]
            let filteredKeys = Array(envVars.keys)
                .filter { envFilter.isEmpty || $0.localizedCaseInsensitiveContains(envFilter) }
                .sorted()

            VStack(alignment: .leading, spacing: 8) {
                TextField("Filter keys", text: $envFilter)

                ForEach(filteredKeys, id: \.self) { key in
                    VStack(spacing: 6) {
                        HStack {
                            Text(key)
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Spacer()
                            Button(action: {
                                config.envVars.wrappedValue?.removeValue(forKey: key)
                            }) {
                                Image(systemName: "trash")
                            }
                            .buttonStyle(.plain)
                        }
                        TextField("Value", text: Binding(
                            get: { envVars[key] ?? "" },
                            set: {
                                if config.envVars.wrappedValue == nil {
                                    config.envVars.wrappedValue = [:]
                                }
                                config.envVars.wrappedValue?[key] = $0
                            }
                        ))
                    }
                    .padding(8)
                    .background(Color(NSColor.windowBackgroundColor))
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                }

                HStack {
                    TextField("KEY", text: $newEnvKey)
                    TextField("VALUE", text: $newEnvValue)
                    Button(action: {
                        if !newEnvKey.isEmpty {
                            if config.envVars.wrappedValue == nil {
                                config.envVars.wrappedValue = [:]
                            }
                            config.envVars.wrappedValue?[newEnvKey] = newEnvValue
                            newEnvKey = ""
                            newEnvValue = ""
                        }
                    }) {
                        Image(systemName: "plus.circle.fill")
                    }
                    .buttonStyle(.plain)
                    .disabled(newEnvKey.isEmpty)
                }

                Text("Changes apply after Save.")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
    }

    private func advancedSection(_ config: Binding<DragonglassConfig>) -> some View {
        DisclosureGroup("Advanced") {
            VStack(alignment: .leading, spacing: 12) {
                Toggle("Close popover when clicking another window", isOn: $closePopoverOnFocusLoss)
                environmentSection(config)
            }
            .padding(.top, 8)
        }
        .font(.caption)
        .foregroundColor(.secondary)
        .padding(.horizontal, 2)
    }

    private func loadConfig() {
        Task {
            do {
                let loaded = try await client.fetchConfig()
                self.config = loaded
                self.baselineConfig = loaded
                self.saveMessage = nil
                self.isLoading = false
            } catch {
                self.errorMessage = "Failed to load config: \(error.localizedDescription)"
                self.showError = true
                self.isLoading = false
            }
        }
    }

    private func saveConfig() {
        guard let config = config else { return }
        Task {
            do {
                await MainActor.run {
                    self.isSaving = true
                }
                try await client.setConfig(config)
                await MainActor.run {
                    self.isSaving = false
                    self.baselineConfig = config
                    self.saveMessage = "Saved"
                }
            } catch {
                await MainActor.run {
                    self.isSaving = false
                    self.errorMessage = "Failed to save config: \(error.localizedDescription)"
                    self.showError = true
                }
            }
        }
    }

    private var hasUnsavedChanges: Bool {
        guard let current = config, let baseline = baselineConfig else {
            return false
        }
        return current != baseline
    }

    @ViewBuilder
    private func settingsSection<Content: View>(
        _ title: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
            content()
        }
        .padding(10)
        .background(Color(NSColor.controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

@MainActor
final class SetupWindowController: NSObject, NSWindowDelegate {
    static let shared = SetupWindowController()

    private var window: NSWindow?
    private var onComplete: ((String) -> Void)?

    func show(onComplete: ((String) -> Void)? = nil) {
        self.onComplete = onComplete

        if let window {
            NSApp.activate(ignoringOtherApps: true)
            window.orderFrontRegardless()
            window.makeKeyAndOrderFront(nil)
            return
        }

        let isPresented = Binding<Bool>(
            get: { self.window != nil },
            set: { visible in
                if !visible {
                    self.closeWindow()
                }
            }
        )

        let rootView = ObsidianSetupView(
            isPresented: isPresented,
            onComplete: { [weak self] vaultPath in
                self?.onComplete?(vaultPath)
            }
        )
        let host = NSHostingController(rootView: rootView)
        let setupWindow = NSWindow(contentViewController: host)
        setupWindow.title = "Obsidian Setup"
        setupWindow.styleMask = [.titled, .closable]
        setupWindow.level = .floating
        setupWindow.collectionBehavior = [.moveToActiveSpace, .fullScreenAuxiliary]
        setupWindow.isReleasedWhenClosed = false
        setupWindow.delegate = self
        setupWindow.center()

        window = setupWindow

        NSApp.activate(ignoringOtherApps: true)
        setupWindow.orderFrontRegardless()
        setupWindow.makeKeyAndOrderFront(nil)
    }

    func windowWillClose(_ notification: Notification) {
        if let closedWindow = notification.object as? NSWindow, closedWindow == window {
            window = nil
            onComplete = nil
        }
    }

    private func closeWindow() {
        guard let window else { return }
        self.window = nil
        window.close()
    }
}
