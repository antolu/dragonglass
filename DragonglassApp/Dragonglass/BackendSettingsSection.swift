import SwiftUI

struct BackendSettingsSection: View {
    @EnvironmentObject var client: AgentClient
    @Binding var config: DragonglassConfig

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            let opencodeAvailable = config.opencodeAvailable ?? true
            let opencodeDisabledReason = config.opencodeDisabledReason

            HStack {
                Text("Backend")
                Spacer()
                Picker("", selection: $config.llmBackend) {
                    Text("LiteLLM").tag("litellm")
                    Text("OpenCode")
                        .tag("opencode")
                        .disabled(!opencodeAvailable)
                        .help(opencodeDisabledReason ?? "OpenCode is unavailable")
                }
                .pickerStyle(.segmented)
                .fixedSize()
                .onChange(of: config.llmBackend) { _, newBackend in
                    config.selectedModel = ""
                    client.setBackend(newBackend)
                }
            }

            if !opencodeAvailable {
                Text(opencodeDisabledReason ?? "OpenCode is unavailable")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            if config.llmBackend == "opencode" {
                HStack {
                    Text("Spawn Managed Server")
                    Spacer()
                    Toggle("", isOn: $config.spawnOpencode)
                        .toggleStyle(.switch)
                        .controlSize(.small)
                        .labelsHidden()
                }
            }
        }
    }
}
