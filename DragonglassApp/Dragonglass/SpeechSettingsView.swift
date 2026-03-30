import AppKit
import SwiftUI

struct SpeechSettingsView: View {
    @EnvironmentObject var sttManager: STTManager
    @EnvironmentObject var hotkeyManager: HotkeyManager
    @AppStorage("sttHotkeyKeyCode") private var hotkeyKeyCode: Int = 0
    @AppStorage("sttHotkeyModifiers") private var hotkeyModifiers: Int = 0
    @AppStorage("sttAutoSend") private var autoSend: Bool = true

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            micPermissionRow

            Divider()

            HStack {
                Text("Auto-send after 1s")
                Spacer()
                Toggle("", isOn: $autoSend)
                    .toggleStyle(.switch)
                    .controlSize(.small)
                    .labelsHidden()
            }

            hotkeyRow

            if !hotkeyManager.accessibilityGranted {
                accessibilityWarning
            }

            Divider()

            HStack {
                Text("Whisper model")
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()
                if sttManager.isModelLoading {
                    ProgressView()
                        .scaleEffect(0.6)
                        .frame(height: 14)
                    Text("Loading…")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }

            if sttManager.availableModels.isEmpty {
                ProgressView("Fetching model list…")
                    .font(.caption)
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                VStack(spacing: 2) {
                    ForEach(sttManager.availableModels, id: \.self) { model in
                        ModelRowView(modelName: model)
                            .environmentObject(sttManager)
                    }
                }
            }
        }
        .onAppear {
            sttManager.refreshLocalModels()
            sttManager.checkAccessibilityPermission()
            hotkeyManager.refreshAccessibility()
            Task { await sttManager.fetchAvailableModels() }
        }
    }

    private var micPermissionRow: some View {
        HStack {
            Image(systemName: sttManager.micPermissionGranted ? "mic.fill" : "mic.slash")
                .foregroundColor(sttManager.micPermissionGranted ? .green : .orange)
            Text(sttManager.micPermissionGranted ? "Microphone granted" : "Microphone required")
                .font(.caption)
            Spacer()
            if !sttManager.micPermissionGranted {
                Button("Grant") { Task { await sttManager.requestMicPermission() } }
                    .buttonStyle(.plain)
                    .foregroundColor(.accentColor)
                    .font(.caption)
                Button("Settings") {
                    NSWorkspace.shared.open(
                        URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone")!
                    )
                }
                .buttonStyle(.plain)
                .foregroundColor(.secondary)
                .font(.caption)
            }
        }
    }

    private var hotkeyRow: some View {
        HStack {
            Text("Hold-to-record hotkey")
                .font(.caption)
            Spacer()
            KeyRecorderView(
                keyCode: $hotkeyKeyCode,
                modifiers: $hotkeyModifiers,
                onChanged: { hotkeyManager.registerIfPossible() }
            )
            .frame(width: 110, height: 22)
            .disabled(!hotkeyManager.accessibilityGranted)
            .opacity(hotkeyManager.accessibilityGranted ? 1.0 : 0.4)
        }
    }

    private var accessibilityWarning: some View {
        HStack(spacing: 6) {
            Image(systemName: "exclamationmark.triangle")
                .foregroundColor(.orange)
                .font(.caption)
            Text("Accessibility access required for global hotkey")
                .font(.caption2)
                .foregroundColor(.secondary)
            Spacer()
            Button("Open Settings") {
                NSWorkspace.shared.open(
                    URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")!
                )
            }
            .buttonStyle(.plain)
            .foregroundColor(.accentColor)
            .font(.caption2)
        }
    }
}

struct ModelRowView: View {
    let modelName: String
    @EnvironmentObject var sttManager: STTManager

    private var isLocal: Bool { sttManager.localModels.contains(modelName) }
    private var isActive: Bool { sttManager.selectedModel == modelName }
    private var progress: Double? { sttManager.downloadProgress[modelName] }

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: isActive ? "checkmark.circle.fill" : "circle")
                .foregroundColor(isActive ? .accentColor : .clear)
                .frame(width: 14)
                .font(.caption)

            Text(modelName)
                .font(.caption)
                .lineLimit(1)

            Spacer()

            if let p = progress {
                ProgressView(value: p)
                    .frame(width: 70)
                    .controlSize(.small)
                Text("\(Int(p * 100))%")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            } else if isLocal {
                Text(diskSize())
                    .font(.caption2)
                    .foregroundColor(.secondary)
                Button("Delete") { sttManager.deleteModel(modelName) }
                    .buttonStyle(.plain)
                    .foregroundColor(.red)
                    .font(.caption2)
            } else {
                Button("Download") { sttManager.downloadModel(modelName) }
                    .buttonStyle(.plain)
                    .foregroundColor(.accentColor)
                    .font(.caption2)
            }
        }
        .padding(.vertical, 2)
        .contentShape(Rectangle())
        .onTapGesture {
            if isLocal { sttManager.switchModel(to: modelName) }
        }
    }

    private func diskSize() -> String {
        let folder = URL(fileURLWithPath: sttManager.modelRepoPath).appendingPathComponent(modelName)
        guard let enumerator = FileManager.default.enumerator(
            at: folder,
            includingPropertiesForKeys: [.fileSizeKey],
            options: [.skipsHiddenFiles]
        ) else { return "" }
        var total = 0
        for case let file as URL in enumerator {
            total += (try? file.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0
        }
        guard total > 0 else { return "" }
        return ByteCountFormatter.string(fromByteCount: Int64(total), countStyle: .file)
    }
}
