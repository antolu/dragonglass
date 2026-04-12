import AppKit
import SwiftUI

struct SpeechSettingsView: View {
    @EnvironmentObject var sttManager: STTManager
    @EnvironmentObject var hotkeyManager: HotkeyManager
    @AppStorage("sttHotkeyKeyCode") private var hotkeyKeyCode: Int = 0
    @AppStorage("sttHotkeyModifiers") private var hotkeyModifiers: Int = 0
    @AppStorage("sttAutoSend") private var autoSend: Bool = true
    @AppStorage("dictationToggleThreshold") private var dictationToggleThreshold: Double = 10.0
    @AppStorage("dictationHotkeyKeyCode") private var dictationHotkeyKeyCode: Int = 0
    @AppStorage("dictationHotkeyModifiers") private var dictationHotkeyModifiers: Int = 0

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
            dictationHotkeyRow

            dictationModeRow

            if !hotkeyManager.accessibilityGranted {
                accessibilityWarning
            }

            Divider()

            modelListSection
        }
        .onAppear {
            sttManager.refreshLocalModels()
            sttManager.checkAccessibilityPermission()
            hotkeyManager.refreshAccessibility()
            Task { await sttManager.fetchAvailableModels() }
        }
    }

    @State private var modelsExpanded = false

    private var unusedLocalModels: [String] {
        sttManager.localModels.filter { $0 != sttManager.selectedModel }
    }

    private var modelListSection: some View {
        DisclosureGroup(isExpanded: $modelsExpanded) {
            VStack(spacing: 2) {
                if sttManager.availableModels.isEmpty {
                    ProgressView("Fetching model list…")
                        .font(.caption)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.top, 4)
                } else {
                    ForEach(sttManager.availableModels, id: \.self) { model in
                        ModelRowView(modelName: model)
                            .environmentObject(sttManager)
                    }
                }
            }
            .padding(.top, 4)
        } label: {
            HStack {
                Text("Whisper model")
                    .font(.caption)
                    .foregroundColor(.secondary)
                if !sttManager.selectedModel.isEmpty {
                    Text(sttManager.selectedModel)
                        .font(.caption)
                        .foregroundColor(.primary)
                }
                Spacer()
                if sttManager.isModelLoading {
                    ProgressView()
                        .scaleEffect(0.6)
                        .frame(height: 14)
                    Text("Loading…")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                if !unusedLocalModels.isEmpty && !modelsExpanded {
                    Button("Clean Up (\(unusedLocalModels.count))") {
                        for model in unusedLocalModels {
                            sttManager.deleteModel(model)
                        }
                    }
                    .buttonStyle(.plain)
                    .foregroundColor(.orange)
                    .font(.caption2)
                }
            }
            .frame(maxWidth: .infinity)
            .contentShape(Rectangle())
            .onTapGesture { modelsExpanded.toggle() }
        }
        .font(.caption)
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

    private var dictationHotkeyRow: some View {
        HStack {
            Text("Dictate-at-cursor hotkey")
                .font(.caption)
            Spacer()
            KeyRecorderView(
                keyCode: $dictationHotkeyKeyCode,
                modifiers: $dictationHotkeyModifiers,
                onChanged: { hotkeyManager.registerIfPossible() }
            )
            .frame(width: 110, height: 22)
            .disabled(!hotkeyManager.accessibilityGranted)
            .opacity(hotkeyManager.accessibilityGranted ? 1.0 : 0.4)
        }
    }

    private var dictationModeRow: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text("Dictation toggle threshold")
                    .font(.caption)
                Spacer()
                if dictationToggleThreshold == 0 {
                    Text("hold only")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                } else {
                    Text("\(Int(dictationToggleThreshold))s")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
            Slider(value: $dictationToggleThreshold, in: 0...30, step: 1)
                .controlSize(.small)
            Text(dictationToggleThreshold == 0
                ? "Always hold to dictate"
                : "Hold < \(Int(dictationToggleThreshold))s = hold-to-dictate, longer = toggle"
            )
            .font(.caption2)
            .foregroundColor(.secondary)
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
    @State private var confirmDownload = false

    private var isLocal: Bool { sttManager.localModels.contains(modelName) }
    private var isActive: Bool { sttManager.selectedModel == modelName }
    private var downloadState: ModelDownloadState? { sttManager.downloadProgress[modelName] }

    private func formatSpeed(_ bps: Double) -> String {
        ByteCountFormatter.string(fromByteCount: Int64(bps), countStyle: .file) + "/s"
    }

    private func formatETA(_ seconds: TimeInterval) -> String {
        if seconds < 60 { return "\(Int(seconds))s" }
        return "\(Int(seconds / 60))m \(Int(seconds.truncatingRemainder(dividingBy: 60)))s"
    }

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

            if let state = downloadState {
                VStack(alignment: .trailing, spacing: 1) {
                    ProgressView(value: state.fraction)
                        .frame(width: 70)
                        .controlSize(.small)
                    HStack(spacing: 4) {
                        Text("\(Int(state.fraction * 100))%")
                        if state.bytesPerSecond > 0 {
                            Text("·")
                            Text(formatSpeed(state.bytesPerSecond))
                            if let eta = state.eta {
                                Text("·")
                                Text(formatETA(eta))
                            }
                        }
                    }
                    .font(.caption2)
                    .foregroundColor(.secondary)
                }
            } else if isLocal {
                Text(diskSize())
                    .font(.caption2)
                    .foregroundColor(.secondary)
                Button("Delete") { sttManager.deleteModel(modelName) }
                    .buttonStyle(.plain)
                    .foregroundColor(.red)
                    .font(.caption2)
            } else {
                if let bytes = sttManager.modelSizes[modelName] {
                    Text(ByteCountFormatter.string(fromByteCount: Int64(bytes), countStyle: .file))
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                Button("Download") { sttManager.downloadModel(modelName) }
                    .buttonStyle(.plain)
                    .foregroundColor(.accentColor)
                    .font(.caption2)
            }
        }
        .padding(.vertical, 2)
        .contentShape(Rectangle())
        .onTapGesture {
            if isLocal {
                sttManager.switchModel(to: modelName)
            } else if downloadState == nil {
                confirmDownload = true
            }
        }
        .confirmationDialog("Download \(modelName)?", isPresented: $confirmDownload) {
            Button("Download") { sttManager.downloadModel(modelName) }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This model is not downloaded yet.")
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
