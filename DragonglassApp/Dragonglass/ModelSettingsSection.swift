import SwiftUI

struct ModelSettingsSection: View {
    @Binding var config: DragonglassConfig

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Default Model")
                .font(.caption)
                .foregroundColor(.secondary)
            TextField("Default Model", text: $config.llmModel)
        }
    }
}
