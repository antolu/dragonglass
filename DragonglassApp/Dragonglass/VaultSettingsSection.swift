import SwiftUI

struct VaultSettingsSection: View {
    @EnvironmentObject var client: AgentClient
    @Binding var config: DragonglassConfig
    let onSaved: (DragonglassConfig) -> Void
    let onError: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text(config.obsidianDir.isEmpty ? "Not configured" : "Configured")
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(
                        config.obsidianDir.isEmpty
                            ? Color.orange.opacity(0.2)
                            : Color.green.opacity(0.2)
                    )
                    .clipShape(Capsule())
                Spacer()
                Button("Change…") {
                    SetupWindowController.shared.show { vaultPath in
                        var updated = config
                        Task {
                            updated.obsidianDir = vaultPath
                            do {
                                try await client.setConfig(updated)
                                await MainActor.run {
                                    onSaved(updated)
                                }
                            } catch {
                                await MainActor.run {
                                    onError("Failed to save vault path: \(error.localizedDescription)")
                                }
                            }
                        }
                    }
                }
                .buttonStyle(.plain)
                .foregroundColor(.accentColor)
            }

            HStack(spacing: 6) {
                Text(config.obsidianDir.isEmpty ? "Not configured" : config.obsidianDir)
                    .font(.system(.caption, design: .monospaced))
                    .foregroundColor(config.obsidianDir.isEmpty ? .secondary : .primary)
                    .lineLimit(1)
                    .truncationMode(.middle)
                Spacer()
                if !config.obsidianDir.isEmpty {
                    Button {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(config.obsidianDir, forType: .string)
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
