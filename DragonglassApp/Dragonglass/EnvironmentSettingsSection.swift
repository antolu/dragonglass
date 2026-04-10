import SwiftUI

struct EnvironmentSettingsSection: View {
    @Binding var config: DragonglassConfig
    @Binding var newEnvKey: String
    @Binding var newEnvValue: String
    @Binding var envFilter: String

    var body: some View {
        let envVars = config.envVars ?? [:]
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
                            config.envVars?.removeValue(forKey: key)
                        }) {
                            Image(systemName: "trash")
                        }
                        .buttonStyle(.plain)
                    }
                    TextField("Value", text: Binding(
                        get: { envVars[key] ?? "" },
                        set: {
                            if config.envVars == nil {
                                config.envVars = [:]
                            }
                            config.envVars?[key] = $0
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
                        if config.envVars == nil {
                            config.envVars = [:]
                        }
                        config.envVars?[newEnvKey] = newEnvValue
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
