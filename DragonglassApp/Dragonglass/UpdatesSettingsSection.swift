import SwiftUI

struct UpdatesSettingsSection: View {
    @EnvironmentObject var updateChecker: UpdateChecker
    @AppStorage("updateChecker.disabled") private var disabled = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Toggle("Check for updates automatically", isOn: Binding(
                get: { !disabled },
                set: { disabled = !$0; updateChecker.startPeriodicChecks(disabled: disabled) }
            ))
            .toggleStyle(.switch)

            HStack {
                if updateChecker.isChecking {
                    ProgressView()
                        .scaleEffect(0.7)
                        .frame(width: 14, height: 14)
                    Text("Checking...")
                        .font(.caption)
                        .foregroundColor(.secondary)
                } else if let latest = updateChecker.latestVersion,
                          let current = updateChecker.currentVersion() {
                    if updateChecker.hasUpdate() {
                        Label("Update available: \(latest) (current: \(current))", systemImage: "arrow.down.circle")
                            .font(.caption)
                            .foregroundColor(.orange)
                    } else {
                        Label("Up to date (\(current))", systemImage: "checkmark.circle")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                } else if let err = updateChecker.checkError {
                    Label("Check failed: \(err)", systemImage: "exclamationmark.triangle")
                        .font(.caption)
                        .foregroundColor(.red)
                }
                Spacer()
                Button("Check Now") {
                    updateChecker.checkNow()
                }
                .font(.caption)
                .buttonStyle(.plain)
                .foregroundColor(.accentColor)
                .disabled(updateChecker.isChecking)
            }
        }
    }
}
