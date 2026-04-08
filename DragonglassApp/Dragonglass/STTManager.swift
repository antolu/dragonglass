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
    @Published var modelSizes: [String: Int] = [:]
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

    @Published var isCursorDictating = false
    private var cursorSession: CursorDictationSession?
    private var lastCursorText: String = ""

    private var whisperKit: WhisperKit?
    private var loadTask: Task<WhisperKit, Error>?
    private var streamTranscriber: AudioStreamTranscriber?
    private var streamTask: Task<Void, Never>?
    private var autoSendTask: Task<Void, Never>?

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
        modelSizes = Self.loadManifestSizes()
    }

    private static func loadManifestSizes() -> [String: Int] {
        guard let url = Bundle.main.url(forResource: "whisper_models", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let models = json["models"] as? [[String: Any]]
        else { return [:] }
        var sizes: [String: Int] = [:]
        for entry in models {
            if let name = entry["name"] as? String, let bytes = entry["size_bytes"] as? Int {
                sizes[name] = bytes
            }
        }
        return sizes
    }

    func downloadModel(_ modelName: String) {
        guard downloadProgress[modelName] == nil else { return }
        logger.debug("Starting download for model: \(modelName)")
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
                logger.debug("Download completed for: \(modelName)")
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
        logger.debug("Switching model to: \(modelName)")
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

        logger.debug("Initializing WhisperKit with model: \(model)")
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
            logger.debug("WhisperKit loaded successfully")
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
        guard let wk = whisperKit, let tokenizer = wk.tokenizer else {
            logger.warning("startRecording failed: whisperKit not ready")
            return
        }

        logger.debug("Starting recording...")
        autoSendTask?.cancel()
        autoSendTask = nil
        pendingText = nil
        readyToFire = false

        startTranscriber(wk: wk, tokenizer: tokenizer) { [weak self] full in
            guard let self else { return }
            self.pendingText = full
        }
    }

    func startCursorDictation() {
        guard !isRecording, micPermissionGranted, isModelReady else {
            logger.warning("startCursorDictation failed: isRecording=\(self.isRecording), micGranted=\(self.micPermissionGranted), isModelReady=\(self.isModelReady)")
            return
        }
        guard let wk = whisperKit, let tokenizer = wk.tokenizer else {
            logger.warning("startCursorDictation failed: whisperKit not ready")
            return
        }
        guard let session = CursorDictationSession.start() else {
            logger.warning("startCursorDictation failed: could not acquire AX session")
            return
        }

        logger.debug("Starting cursor dictation...")
        cursorSession = session
        isCursorDictating = true
        lastCursorText = ""

        startTranscriber(wk: wk, tokenizer: tokenizer) { [weak self] full in
            guard let self, let session = self.cursorSession else { return }
            if session.checkDrift() {
                logger.debug("Drift detected — stopping cursor dictation")
                // Don't call stopCursorDictation (already mid-callback); just clean up
                self.isCursorDictating = false
                self.cursorSession = nil
                session.finish()
                self.stopTranscriber()
                return
            }
            self.lastCursorText = full
            session.update(text: full)
        }
    }

    func stopCursorDictation() {
        guard isCursorDictating else { return }
        logger.debug("Stopping cursor dictation — waiting for tail")
        isCursorDictating = false
        let session = cursorSession
        cursorSession = nil

        let transcriber = streamTranscriber
        streamTranscriber = nil
        streamTask = nil

        Task {
            // Give Whisper ~500ms of silence to finalize the last segment
            try? await Task.sleep(nanoseconds: 500_000_000)
            await transcriber?.stopStreamTranscription()
            // After stop, take whatever the last emitted text was (includes currentText)
            await MainActor.run {
                let final = self.lastCursorText
                self.isRecording = false
                if !final.isEmpty {
                    session?.update(text: final)
                }
                session?.finish()
                logger.info("Cursor dictation finished with: \"\(final)\"")
            }
        }
    }

    private func startTranscriber(wk: WhisperKit, tokenizer: any WhisperTokenizer, onSegment: @escaping @MainActor (String) -> Void) {
        let transcriber = AudioStreamTranscriber(
            audioEncoder: wk.audioEncoder,
            featureExtractor: wk.featureExtractor,
            segmentSeeker: wk.segmentSeeker,
            textDecoder: wk.textDecoder,
            tokenizer: tokenizer,
            audioProcessor: wk.audioProcessor,
            decodingOptions: DecodingOptions(
                temperature: 0.0,
                skipSpecialTokens: true
            ),
            requiredSegmentsForConfirmation: 2,
            useVAD: true
        ) { [weak self] _, newState in
            guard self != nil else { return }
            let confirmed = newState.confirmedSegments.map { $0.text }.joined()
            let current = newState.currentText
            let full = (confirmed + " " + current).trimmingCharacters(in: .whitespacesAndNewlines)
            guard !full.isEmpty, full != "Waiting for speech..." else { return }
            Task { @MainActor in onSegment(full) }
        }

        streamTranscriber = transcriber
        isRecording = true

        streamTask = Task {
            do {
                try await transcriber.startStreamTranscription()
            } catch is CancellationError {
                // expected on stop
            } catch {
                logger.error("Streaming transcription error: \(error.localizedDescription)")
            }
            await MainActor.run { self.isRecording = false }
        }

        logger.debug("Recording started successfully")
    }

    func stopAndTranscribe() {
        guard isRecording, !isCursorDictating else { return }
        logger.debug("Stopping recording")
        let transcriber = streamTranscriber
        streamTranscriber = nil
        streamTask = nil
        isRecording = false

        Task {
            await transcriber?.stopStreamTranscription()
            await MainActor.run {
                guard let text = self.pendingText, !text.isEmpty else { return }
                logger.info("Final transcription: \"\(text)\"")
                if self.autoSend { self.scheduleAutoSend() }
            }
        }
    }

    private func stopTranscriber() {
        guard isRecording else { return }
        let transcriber = streamTranscriber
        streamTranscriber = nil
        streamTask = nil
        isRecording = false
        Task { await transcriber?.stopStreamTranscription() }
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

    func cancelRecording() {
        guard isRecording, !isCursorDictating else { return }
        logger.debug("Recording cancelled")
        stopTranscriber()
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
