import SwiftUI

struct PermissionsSettingsSection: View {
    @Binding var config: DragonglassConfig

    var body: some View {
        VStack(spacing: 8) {
            HStack {
                Text("Auto-allow Edits")
                Spacer()
                Toggle("", isOn: $config.autoAllowEdit)
                    .toggleStyle(.switch)
                    .controlSize(.small)
                    .labelsHidden()
            }
            HStack {
                Text("Auto-allow Create")
                Spacer()
                Toggle("", isOn: $config.autoAllowCreate)
                    .toggleStyle(.switch)
                    .controlSize(.small)
                    .labelsHidden()
            }
            HStack {
                Text("Auto-allow Delete")
                Spacer()
                Toggle("", isOn: $config.autoAllowDelete)
                    .toggleStyle(.switch)
                    .controlSize(.small)
                    .labelsHidden()
            }
        }
    }
}
