import SwiftUI
import AppKit

struct SettingsView: View {
    @Binding var isPresented: Bool
    @EnvironmentObject var client: AgentClient
    @EnvironmentObject var sttManager: STTManager
    @EnvironmentObject var hotkeyManager: HotkeyManager

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
                        settingsSection("Obsidian Vault") {
                            VaultSettingsSection(
                                config: config,
                                onSaved: { updated in
                                    self.config = updated
                                    self.baselineConfig = updated
                                    self.saveMessage = "Saved"
                                },
                                onError: { msg in
                                    self.errorMessage = msg
                                    self.showError = true
                                }
                            )
                            .environmentObject(client)
                        }
                        settingsSection("Model") {
                            ModelSettingsSection(config: config)
                        }
                        settingsSection("LLM Backend") {
                            BackendSettingsSection(config: config)
                                .environmentObject(client)
                        }
                        settingsSection("Permissions") {
                            PermissionsSettingsSection(config: config)
                        }
                        settingsSection("Interface") {
                            UISettingsSection()
                                .environmentObject(client)
                        }
                        settingsSection("Speech to Text") {
                            SpeechSettingsView()
                                .environmentObject(sttManager)
                                .environmentObject(hotkeyManager)
                        }
                        DisclosureGroup("Advanced") {
                            VStack(alignment: .leading, spacing: 12) {
                                settingsSection("Environment Variables") {
                                    EnvironmentSettingsSection(
                                        config: config,
                                        newEnvKey: $newEnvKey,
                                        newEnvValue: $newEnvValue,
                                        envFilter: $envFilter
                                    )
                                }
                            }
                            .padding(.top, 8)
                        }
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.horizontal, 2)
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
            .foregroundColor(.red)
            .focusable(false)
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color(NSColor.windowBackgroundColor))
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
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(Color(NSColor.controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}
