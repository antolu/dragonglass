import SwiftUI

struct SettingsView: View {
    @Binding var isPresented: Bool
    @EnvironmentObject var client: AgentClient

    @State private var config: DragonglassConfig?
    @State private var isLoading = true

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Settings")
                    .font(.headline)
                Spacer()
                Button(action: { isPresented = false }) {
                    Image(systemName: "xmark")
                }
                .buttonStyle(.plain)
                .focusable(false)
            }
            .padding()

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
                }
                .padding()
            } else {
                Spacer()
            }

            Divider()

            HStack {
                Button("Cancel") { isPresented = false }
                Button("Save") {
                    saveConfig()
                }
                .buttonStyle(.borderedProminent)

                Spacer()

                Button("Quit") {
                    NSApplication.shared.terminate(nil)
                }
                .foregroundColor(.red)
            }
            .padding()
        }
        .frame(width: 300, height: 500)
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
