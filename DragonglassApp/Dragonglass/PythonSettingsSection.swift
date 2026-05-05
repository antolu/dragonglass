import SwiftUI

struct PythonSettingsSection: View {
    @EnvironmentObject var backend: BackendManager
    @State private var selectedPath: String = getSelectedPythonPath() ?? ""

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text(selectedPath.isEmpty ? "Not configured" : "Configured")
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(
                        selectedPath.isEmpty
                            ? Color.orange.opacity(0.2)
                            : Color.green.opacity(0.2)
                    )
                    .clipShape(Capsule())
                Spacer()
                Button("Change…") {
                    SetupWindowController.shared.showPythonSetup(backend: backend)
                }
                .buttonStyle(.plain)
                .foregroundColor(.accentColor)
            }

            Text(selectedPath.isEmpty ? "Not configured" : selectedPath)
                .font(.system(.caption, design: .monospaced))
                .foregroundColor(selectedPath.isEmpty ? .secondary : .primary)
                .lineLimit(1)
                .truncationMode(.middle)
        }
        .onReceive(NotificationCenter.default.publisher(for: UserDefaults.didChangeNotification)) { _ in
            selectedPath = getSelectedPythonPath() ?? ""
        }
    }
}
