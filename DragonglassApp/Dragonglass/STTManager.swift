import AVFoundation
import Combine
import WhisperKit
import os

private let logger = Logger(subsystem: "com.antolu.dragonglass", category: "STTManager")

@MainActor
final class STTManager: ObservableObject {
    @Published var isRecording = false
    @Published var isTranscribing = false
    @Published var isModelLoading = false
    @Published var pendingText: String?
    @Published var readyToFire = false
    @Published var downloadProgress: [String: Double] = [:]
    @Published var availableModels: [String] = []
    @Published var localModels: [String] = []
    @Published var micPermissionGranted = false
    @Published var accessibilityGranted = false

    var selectedModel: String {
        get { UserDefaults.standard.string(forKey: "sttSelectedModel") ?? "openai_whisper-large-v3-v20240930_turbo" }
        set { UserDefaults.standard.set(newValue, forKey: "sttSelectedModel") }
    }

    var isModelReady: Bool { localModels.contains(selectedModel) }

    var autoSend: Bool {
        get { UserDefaults.standard.object(forKey: "sttAutoSend") as? Bool ?? true }
        set { UserDefaults.standard.set(newValue, forKey: "sttAutoSend") }
    }

    private static let repoName = "argmaxinc/whisperkit-coreml"

    private var whisperKit: WhisperKit?
    private var loadTask: Task<WhisperKit, Error>?
    private var audioEngine: AVAudioEngine!
    private var audioSamples: [Float] = []
    private var converter: AVAudioConverter?
    private var autoSendTask: Task<Void, Never>?
    private let audioQueue = DispatchQueue(label: "com.antolu.dragonglass.audio", qos: .userInteractive)

    private final class AudioBuffer: @unchecked Sendable {
        var samples: [Float] = []
        var tapCount: Int = 0
    }
    private let audioBuffer = AudioBuffer()

    init() {
        logger.debug("Initializing STTManager")
        checkMicPermission()
        checkAccessibilityPermission()
        refreshLocalModels()
        Task { await fetchAvailableModels() }
        Task { try? await ensureLoaded() }
    }

    // MARK: - Permissions

    func checkMicPermission() {
        micPermissionGranted = AVAudioApplication.shared.recordPermission == .granted
    }

    func requestMicPermission() async {
        let granted = await AVAudioApplication.requestRecordPermission()
        micPermissionGranted = granted
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

    var modelRepoPath: String {
        URL(fileURLWithPath: localModelPath)
            .appendingPathComponent("models/argmaxinc/whisperkit-coreml")
            .path
    }

    func refreshLocalModels() {
        try? FileManager.default.createDirectory(atPath: modelRepoPath, withIntermediateDirectories: true)
        let contents = (try? FileManager.default.contentsOfDirectory(atPath: modelRepoPath)) ?? []
        // Only include non-hidden directories (ignore .cache, etc.)
        let models = contents.filter { !$0.hasPrefix(".") }
        localModels = models
        logger.debug("Refreshed local models: \(models)")
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
        logger.info("Starting download for model: \(modelName)")
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
                logger.info("Download completed for: \(modelName)")
                await MainActor.run {
                    self.downloadProgress.removeValue(forKey: modelName)
                    self.refreshLocalModels()
                    if self.selectedModel == modelName {
                        self.loadTask?.cancel()
                        self.loadTask = nil
                        self.whisperKit = nil
                        Task { try? await self.ensureLoaded() }
                    }
                }
            } catch {
                logger.error("Download failed for \(modelName): \(error.localizedDescription)")
                let name = modelName
                await MainActor.run { _ = self.downloadProgress.removeValue(forKey: name) }
            }
        }
    }

    func deleteModel(_ modelName: String) {
        let folderURL = URL(fileURLWithPath: modelRepoPath).appendingPathComponent(modelName)
        try? FileManager.default.removeItem(at: folderURL)
        if selectedModel == modelName {
            whisperKit = nil
        }
        refreshLocalModels()
    }

    func switchModel(to modelName: String) {
        guard modelName != selectedModel else { return }
        logger.info("Switching model to: \(modelName)")
        objectWillChange.send()
        selectedModel = modelName
        loadTask?.cancel()
        loadTask = nil
        Task { await self.whisperKit?.unloadModels() }
        whisperKit = nil
        Task { try? await ensureLoaded() }
    }

    // MARK: - WhisperKit loading

    private func ensureLoaded() async throws {
        if let wk = whisperKit {
            logger.debug("Model already loaded: \(wk.modelVariant)")
            return
        }
        if let task = loadTask {
            logger.debug("Awaiting existing load task")
            whisperKit = try await task.value
            return
        }
        let model = selectedModel.isEmpty ? "openai_whisper-large-v3-v20240930_turbo" : selectedModel
        let repoURL = URL(fileURLWithPath: modelRepoPath)
        let modelFolder = repoURL.appendingPathComponent(model)

        logger.info("Initializing WhisperKit with model: \(model)")
        logger.debug("Model folder: \(modelFolder.path)")

        guard FileManager.default.fileExists(atPath: modelFolder.path) else {
            logger.warning("Model folder does not exist: \(modelFolder.path)")
            throw STTError.notDownloaded
        }

        let config = WhisperKitConfig(
            model: model,
            downloadBase: URL(fileURLWithPath: localModelPath),
            modelFolder: modelFolder.path,
            load: true,
            download: false
        )
        let task = Task<WhisperKit, Error> { try await WhisperKit(config) }
        loadTask = task
        isModelLoading = true
        defer {
            loadTask = nil
            isModelLoading = false
        }
        do {
            whisperKit = try await task.value
            logger.info("WhisperKit loaded successfully")
        } catch {
            logger.error("Failed to load WhisperKit: \(error.localizedDescription)")
            throw error
        }
    }

    // MARK: - Recording

    func startRecording() {
        guard !isRecording, micPermissionGranted, isModelReady else {
            logger.warning("startRecording failed: isRecording=\(self.isRecording), micGranted=\(self.micPermissionGranted), isModelReady=\(self.isModelReady)")
            return
        }
        logger.info("Starting recording...")
        autoSendTask?.cancel()
        autoSendTask = nil
        pendingText = nil
        readyToFire = false
        audioSamples = []

        do {
            audioEngine = AVAudioEngine()
            let inputNode = audioEngine.inputNode
            let hwFormat = inputNode.inputFormat(forBus: 0)
            logger.debug("Input format: \(hwFormat)")
            guard hwFormat.sampleRate > 0, hwFormat.channelCount > 0 else {
                logger.error("Invalid hardware format: rate=\(hwFormat.sampleRate), channels=\(hwFormat.channelCount)")
                return
            }
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
                var done = false
                var error: NSError?
                converter.convert(to: converted, error: &error) { _, outStatus in
                    if done {
                        outStatus.pointee = .endOfStream
                        return nil
                    }
                    done = true
                    outStatus.pointee = .haveData
                    return buffer
                }
                guard error == nil, converted.frameLength > 0 else { return }
                let count = Int(converted.frameLength)
                let samples = Array(UnsafeBufferPointer(start: channelData[0], count: count))
                self.audioQueue.async {
                    self.audioBuffer.samples.append(contentsOf: samples)
                    self.audioBuffer.tapCount += 1
                    if self.audioBuffer.tapCount % 50 == 0 {
                        logger.debug("Accumulated \(self.audioBuffer.samples.count) samples (tap #\(self.audioBuffer.tapCount))")
                    }
                }
            }

            try audioEngine.start()
            isRecording = true
            audioQueue.async { self.audioBuffer.tapCount = 0 }
            logger.info("Recording started successfully")
        } catch {
            logger.error("audioEngine.start error: \(error.localizedDescription)")
            print("[STTManager] startRecording error: \(error)")
        }
    }

    func stopAndTranscribe() {
        guard isRecording else { return }
        logger.info("Stopping recording and starting transcription")
        audioEngine.inputNode.removeTap(onBus: 0)
        audioEngine.stop()
        isRecording = false

        audioQueue.sync {
            let samples = audioBuffer.samples
            audioBuffer.samples = []
            let currentTapCount = audioBuffer.tapCount
            audioBuffer.tapCount = 0
            logger.debug("Captured \(samples.count) samples (tap count: \(currentTapCount))")

            Task { @MainActor in
                await self.performTranscription(with: samples)
            }
        }
    }

    private func performTranscription(with samples: [Float]) async {
        guard !samples.isEmpty else {
            logger.warning("No samples captured, skipping transcription")
            return
        }

        isTranscribing = true
        do {
            try await ensureLoaded()
            guard let wk = whisperKit else { throw STTError.notLoaded }
            logger.debug("Calling WhisperKit.transcribe")
            let results = await wk.transcribe(audioArrays: [samples])
            let text = results
                .compactMap { $0?.first?.text }
                .joined(separator: " ")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            logger.info("Transcription result: \"\(text)\"")

            self.isTranscribing = false
            guard !text.isEmpty else { return }
            self.pendingText = text
            if self.autoSend {
                self.scheduleAutoSend()
            }
        } catch {
            logger.error("Transcription failed: \(error.localizedDescription)")
            self.isTranscribing = false
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
    case notDownloaded
}
