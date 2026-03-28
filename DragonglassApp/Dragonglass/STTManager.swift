import AVFoundation
import Combine
import WhisperKit

@MainActor
final class STTManager: ObservableObject {
    @Published var isRecording = false
    @Published var isTranscribing = false
    @Published var pendingText: String?
    @Published var readyToFire = false
    @Published var downloadProgress: [String: Double] = [:]
    @Published var availableModels: [String] = []
    @Published var localModels: [String] = []
    @Published var micPermissionGranted = false
    @Published var accessibilityGranted = false

    var selectedModel: String {
        get { UserDefaults.standard.string(forKey: "sttSelectedModel") ?? "openai_whisper-large-v3" }
        set { UserDefaults.standard.set(newValue, forKey: "sttSelectedModel") }
    }

    var autoSend: Bool {
        get { UserDefaults.standard.object(forKey: "sttAutoSend") as? Bool ?? true }
        set { UserDefaults.standard.set(newValue, forKey: "sttAutoSend") }
    }

    private static let repoName = "argmaxinc/whisperkit-coreml"

    private var whisperKit: WhisperKit?
    private var audioEngine = AVAudioEngine()
    private var audioSamples: [Float] = []
    private var converter: AVAudioConverter?
    private var autoSendTask: Task<Void, Never>?

    init() {
        checkMicPermission()
        checkAccessibilityPermission()
        refreshLocalModels()
        Task { await fetchAvailableModels() }
    }

    // MARK: - Permissions

    func checkMicPermission() {
        micPermissionGranted = AVAudioApplication.shared.recordPermission == .granted
    }

    func requestMicPermission() {
        Task {
            let granted = await AVAudioApplication.requestRecordPermission()
            micPermissionGranted = granted
        }
    }

    func checkAccessibilityPermission() {
        accessibilityGranted = AXIsProcessTrusted()
    }

    // MARK: - Model management

    var localModelPath: String {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support")
        return appSupport.appendingPathComponent("dragonglass/whisperkit-models").path
    }

    func refreshLocalModels() {
        let path = localModelPath
        try? FileManager.default.createDirectory(atPath: path, withIntermediateDirectories: true)
        let contents = (try? FileManager.default.contentsOfDirectory(atPath: path)) ?? []
        localModels = ModelUtilities.formatModelFiles(contents)
    }

    func fetchAvailableModels() async {
        let remote = await WhisperKit.recommendedRemoteModels()
        var models = remote.supported.sorted()
        for m in localModels where !models.contains(m) {
            models.insert(m, at: 0)
        }
        availableModels = models
    }

    func downloadModel(_ modelName: String) {
        guard downloadProgress[modelName] == nil else { return }
        downloadProgress[modelName] = 0.0
        let downloadBase = URL(fileURLWithPath: localModelPath)
        Task {
            do {
                _ = try await WhisperKit.download(
                    variant: modelName,
                    downloadBase: downloadBase,
                    from: Self.repoName,
                    progressCallback: { [weak self] progress in
                        Task { @MainActor in
                            self?.downloadProgress[modelName] = progress.fractionCompleted
                        }
                    }
                )
                await MainActor.run {
                    self.downloadProgress.removeValue(forKey: modelName)
                    self.refreshLocalModels()
                    if self.selectedModel == modelName {
                        self.whisperKit = nil
                    }
                }
            } catch {
                let name = modelName
                await MainActor.run { _ = self.downloadProgress.removeValue(forKey: name) }
            }
        }
    }

    func deleteModel(_ modelName: String) {
        let folderURL = URL(fileURLWithPath: localModelPath).appendingPathComponent(modelName)
        try? FileManager.default.removeItem(at: folderURL)
        if selectedModel == modelName {
            whisperKit = nil
        }
        refreshLocalModels()
    }

    func switchModel(to modelName: String) {
        guard modelName != selectedModel else { return }
        selectedModel = modelName
        Task { await self.whisperKit?.unloadModels() }
        whisperKit = nil
    }

    // MARK: - WhisperKit loading

    private func ensureLoaded() async throws {
        guard whisperKit == nil else { return }
        let model = selectedModel.isEmpty ? "openai_whisper-large-v3" : selectedModel
        let base = URL(fileURLWithPath: localModelPath)
        let config = WhisperKitConfig(
            model: model,
            downloadBase: base,
            modelFolder: base.appendingPathComponent(model).path,
            load: true,
            download: false
        )
        whisperKit = try await WhisperKit(config)
    }

    // MARK: - Recording

    func startRecording() {
        guard !isRecording, micPermissionGranted else { return }
        autoSendTask?.cancel()
        autoSendTask = nil
        pendingText = nil
        readyToFire = false
        audioSamples = []

        do {
            audioEngine = AVAudioEngine()
            let inputNode = audioEngine.inputNode
            let hwFormat = inputNode.outputFormat(forBus: 0)
            let targetFormat = AVAudioFormat(
                commonFormat: .pcmFormatFloat32,
                sampleRate: 16000,
                channels: 1,
                interleaved: false
            )!
            converter = AVAudioConverter(from: hwFormat, to: targetFormat)

            inputNode.installTap(onBus: 0, bufferSize: 4096, format: hwFormat) { [weak self] buffer, _ in
                guard let self, let converter = self.converter else { return }
                let ratio = 16000.0 / hwFormat.sampleRate
                let outFrames = AVAudioFrameCount(Double(buffer.frameLength) * ratio + 1)
                guard let converted = AVAudioPCMBuffer(pcmFormat: targetFormat, frameCapacity: outFrames),
                      let channelData = converted.floatChannelData else { return }
                var error: NSError?
                let inputBlock: AVAudioConverterInputBlock = { _, outStatus in
                    outStatus.pointee = .haveData
                    return buffer
                }
                converter.convert(to: converted, error: &error, withInputFrom: inputBlock)
                if error == nil {
                    let count = Int(converted.frameLength)
                    let samples = Array(UnsafeBufferPointer(start: channelData[0], count: count))
                    DispatchQueue.main.async { self.audioSamples.append(contentsOf: samples) }
                }
            }

            try audioEngine.start()
            isRecording = true
        } catch {
            print("[STTManager] startRecording error: \(error)")
        }
    }

    func stopAndTranscribe() {
        guard isRecording else { return }
        audioEngine.inputNode.removeTap(onBus: 0)
        audioEngine.stop()
        isRecording = false

        let samples = audioSamples
        audioSamples = []
        guard !samples.isEmpty else { return }

        isTranscribing = true
        Task {
            do {
                try await ensureLoaded()
                guard let wk = whisperKit else { throw STTError.notLoaded }
                let results = await wk.transcribe(audioArrays: [samples])
                let text = results
                    .compactMap { $0?.first?.text }
                    .joined(separator: " ")
                    .trimmingCharacters(in: .whitespacesAndNewlines)
                await MainActor.run {
                    self.isTranscribing = false
                    guard !text.isEmpty else { return }
                    self.pendingText = text
                    if self.autoSend {
                        self.scheduleAutoSend()
                    }
                }
            } catch {
                await MainActor.run {
                    self.isTranscribing = false
                }
            }
        }
    }

    // MARK: - Auto-send

    private func scheduleAutoSend() {
        autoSendTask?.cancel()
        autoSendTask = Task {
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            guard !Task.isCancelled else { return }
            await MainActor.run { self.readyToFire = true }
        }
    }

    func cancelPending() {
        autoSendTask?.cancel()
        autoSendTask = nil
        pendingText = nil
        readyToFire = false
    }

    func clearFireFlag() {
        readyToFire = false
        pendingText = nil
    }
}

enum STTError: Error {
    case notLoaded
}
