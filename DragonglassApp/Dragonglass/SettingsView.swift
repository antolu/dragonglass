import SwiftUI

struct SettingsView: View {
    @Binding var isPresented: Bool
    @EnvironmentObject var client: AgentClient

    @State private var config: DragonglassConfig?
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var showError = false
    @State private var newEnvKey = ""
    @State private var newEnvValue = ""

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Settings")
                    .font(.headline)
                Spacer()
                Button(action: saveConfig) {
                    HStack(spacing: 4) {
                        Image(systemName: "checkmark")
                        Text("Save")
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.accentColor)
                    .foregroundColor(.white)
                    .cornerRadius(4)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
            .background(Color(NSColor.windowBackgroundColor))

            if isLoading {
                Spacer()
                ProgressView()
                Spacer()
            } else if let config = Binding($config) {
                Form {
                    Section("Obsidian Connection") {
                        TextField("API URL", text: config.obsidianApiUrl)
                        SecureField("API Key", text: config.obsidianApiKey)
                    }

                    Section("Model & Search") {
                        TextField("Default Model", text: config.llmModel)
                        TextField("Vector Search URL", text: config.vectorSearchUrl)
                    }

                    Section("Permissions") {
                        Toggle("Auto-allow Edits", isOn: config.autoAllowEdit)
                        Toggle("Auto-allow Create", isOn: config.autoAllowCreate)
                        Toggle("Auto-allow Delete", isOn: config.autoAllowDelete)
                    }

                    Section("Environment Variables") {
                        let envVars = config.envVars.wrappedValue ?? [:]
                        ForEach(Array(envVars.keys).sorted(), id: \.self) { key in
                            HStack {
                                Text(key)
                                    .frame(width: 80, alignment: .leading)
                                TextField("Value", text: Binding(
                                    get: { envVars[key] ?? "" },
                                    set: {
                                        if config.envVars.wrappedValue == nil {
                                            config.envVars.wrappedValue = [:]
                                        }
                                        config.envVars.wrappedValue?[key] = $0
                                    }
                                ))
                                Button(action: { config.envVars.wrappedValue?.removeValue(forKey: key) }) {
                                    Image(systemName: "trash")
                                }
                                .buttonStyle(.plain)
                            }
                        }

                        HStack {
                            TextField("KEY", text: $newEnvKey)
                                .frame(width: 80)
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
                    }

                    Section {
                        Button("Quit Dragonglass") {
                            NSApplication.shared.terminate(nil)
                        }
                        .foregroundColor(.red)
                    }
                }
                .padding(.horizontal)
            } else {
                Spacer()
            }

            Spacer(minLength: 0)
        }
        .frame(width: 320, height: 400)
        .alert("Error", isPresented: $showError, presenting: errorMessage) { _ in
            Button("OK") { showError = false }
        } message: { message in
            Text(message)
        }
        .onAppear {
            loadConfig()
        }
    }


    private func loadConfig() {
        Task {
            do {
                self.config = try await client.fetchConfig()
                self.isLoading = false
            } catch {
                print("Failed to load config: \(error)")
                self.isLoading = false
            }
        }
    }

    private func saveConfig() {
        guard let config = config else { return }
        Task {
            do {
                try await client.setConfig(config)
                isPresented = false
            } catch {
                print("Failed to save config: \(error)")
            }
        }
    }
}
