import SwiftUI

struct BackendSettingsSection: View {
    @EnvironmentObject var client: AgentClient
    @Binding var config: DragonglassConfig

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Backend")
                Spacer()
                Picker("", selection: $config.llmBackend) {
                    Text("LiteLLM").tag("litellm" as String?)
                    // Text("OpenCode").tag("opencode" as String?)
                }
                .pickerStyle(.segmented)
                .fixedSize()
                .onChange(of: config.llmBackend) { _, newBackend in
                    config.selectedModel = ""
                    client.setBackend(newBackend ?? "litellm")
                }
            }
        }
    }
}
