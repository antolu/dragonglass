import SwiftUI
import AppKit

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
                    .foregroundColor(.accentColor)
                }
                .buttonStyle(.plain)
                .focusable(false)
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
                    Section("Obsidian Vault") {
                        HStack {
                            Text(config.obsidianDir.wrappedValue.isEmpty ? "Not configured" : config.obsidianDir.wrappedValue)
                                .foregroundColor(config.obsidianDir.wrappedValue.isEmpty ? .secondary : .primary)
                                .lineLimit(1)
                                .truncationMode(.middle)
                            Spacer()
                            Button("Change…") {
                                SetupWindowController.shared.show { vaultPath in
                                    if var current = self.config {
                                        current.obsidianDir = vaultPath
                                        self.config = current
                                    }
                                }
                            }
                            .buttonStyle(.plain)
                            .foregroundColor(.accentColor)
                        }
                    }

                    Section("Model & Search") {
                        TextField("Default Model", text: config.llmModel)
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

@MainActor
final class SetupWindowController: NSObject, NSWindowDelegate {
    static let shared = SetupWindowController()

    private var window: NSWindow?
    private var onComplete: ((String) -> Void)?

    func show(onComplete: ((String) -> Void)? = nil) {
        self.onComplete = onComplete

        if let window {
            NSApp.activate(ignoringOtherApps: true)
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
        setupWindow.isReleasedWhenClosed = false
        setupWindow.delegate = self
        setupWindow.center()

        window = setupWindow

        NSApp.activate(ignoringOtherApps: true)
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
