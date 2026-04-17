import AppKit
import Combine
import OSLog
import SwiftUI
import UniformTypeIdentifiers

private let logger = Logger(subsystem: subsystem, category: "PythonSetup")

@MainActor
class PythonSetupViewModel: ObservableObject {
    @Published var candidates: [(path: String, version: String)] = []
    @Published var selectedPath: String = ""
    @Published var isScanning = false
    @Published var isInstalling = false
    @Published var installProgress: Double = 0
    @Published var installLabel: String = ""
    @Published var installError: String?

    private var backend: BackendManager?
    private var phaseCancellable: AnyCancellable?

    func attach(backend: BackendManager) {
        self.backend = backend
        phaseCancellable = backend.$phase.sink { [weak self] phase in
            guard let self else { return }
            switch phase {
            case .checkingBundle:
                self.isInstalling = true
                self.installProgress = 0
                self.installLabel = "Checking bundle…"
                self.installError = nil
            case .downloadingBundle(let progress, let label):
                self.isInstalling = true
                self.installProgress = progress
                self.installLabel = label
                self.installError = nil
            case .installingBundle:
                self.isInstalling = true
                self.installProgress = 1
                self.installLabel = "Installing…"
                self.installError = nil
            case .bundleError(let message):
                self.isInstalling = false
                self.installError = message
            case .starting, .ready:
                self.isInstalling = false
            default:
                break
            }
        }
    }

    func scan() {
        isScanning = true
        Task {
            let found = discoverPythonCandidates()
            candidates = found
            if let existing = getSelectedPythonPath(), found.contains(where: { $0.path == existing }) {
                selectedPath = existing
            } else {
                selectedPath = found.first?.path ?? ""
            }
            isScanning = false
        }
    }

    func confirm() {
        guard !selectedPath.isEmpty, let backend else { return }
        saveSelectedPythonPath(selectedPath)
        logger.info("Python selected path=\(self.selectedPath, privacy: .public)")
        installError = nil

        if backend.isDevVersion, let bundleURL = findBundledTarball(forPythonPath: selectedPath) {
            logger.info("dev build: using bundled tarball \(bundleURL.lastPathComponent, privacy: .public)")
            backend.triggerOfflineInstall(bundleURL: bundleURL)
            return
        }
        Task { await backend.startBackend() }
    }

    private func findBundledTarball(forPythonPath path: String) -> URL? {
        guard let version = getPythonVersion(at: path) else { return nil }
        let bundlesURL = Bundle.main.bundleURL
            .appendingPathComponent("Contents/Resources/bundles")
        guard let files = try? FileManager.default.contentsOfDirectory(
            at: bundlesURL, includingPropertiesForKeys: nil
        ) else { return nil }
        return files.first { url in
            url.lastPathComponent.contains("-py\(version).") && url.pathExtension == "gz"
        }
    }

    func installOffline() {
        guard let backend else { return }
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.init(filenameExtension: "gz")!]
        panel.title = "Select dependency bundle (.tar.gz)"
        panel.prompt = "Install"
        guard panel.runModal() == .OK, let url = panel.url else { return }
        saveSelectedPythonPath(selectedPath)
        backend.triggerOfflineInstall(bundleURL: url)
    }
}

struct PythonSetupView: View {
    @Binding var isPresented: Bool
    @EnvironmentObject var backend: BackendManager
    @StateObject private var vm = PythonSetupViewModel()

    var minVersionLabel: String {
        let v = getMinPythonVersion()
        return "\(v.major).\(v.minor)"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Environment Setup")
                .font(.title2)
                .fontWeight(.semibold)
                .frame(maxWidth: .infinity, alignment: .leading)

            pythonPicker

            Divider()

            installSection
        }
        .padding(32)
        .frame(width: 440)
        .onAppear {
            vm.attach(backend: backend)
            vm.scan()
        }
        .onChange(of: backend.phase) { _, phase in
            if case .starting = phase { isPresented = false }
        }
    }

    private var pythonPicker: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Python")
                .font(.headline)

            Text("Select the Python \(minVersionLabel)+ installation to use as the base for the virtual environment.")
                .foregroundColor(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            if vm.isScanning {
                HStack(spacing: 8) {
                    ProgressView().scaleEffect(0.7)
                    Text("Scanning…").foregroundColor(.secondary)
                }
            } else if vm.candidates.isEmpty {
                Label("No compatible Python \(minVersionLabel)+ found. Install via Homebrew or python.org.", systemImage: "exclamationmark.triangle")
                    .foregroundColor(.orange)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Picker("Python", selection: $vm.selectedPath) {
                    ForEach(vm.candidates, id: \.path) { c in
                        Text("\(c.version)  —  \(c.path)").tag(c.path)
                    }
                }
                .labelsHidden()
            }

            Button("Rescan") { vm.scan() }
                .buttonStyle(.plain)
                .foregroundColor(.secondary)
                .disabled(vm.isScanning)
        }
    }

    private var installSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Bundle")
                .font(.headline)

            if vm.isInstalling {
                VStack(alignment: .leading, spacing: 6) {
                    Text(vm.installLabel)
                        .foregroundColor(.secondary)
                    ProgressView(value: vm.installProgress)
                        .progressViewStyle(.linear)
                }
            } else if let error = vm.installError {
                Label(error, systemImage: "exclamationmark.triangle")
                    .foregroundColor(.red)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Text("Downloads and installs the dragonglass backend for the selected Python version.")
                    .foregroundColor(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack(spacing: 10) {
                Button("from a local file…") { vm.installOffline() }
                    .buttonStyle(.plain)
                    .foregroundColor(.accentColor)
                    .disabled(vm.isInstalling)
                Spacer()
                Button("Install") { vm.confirm() }
                    .buttonStyle(.borderedProminent)
                    .disabled(vm.selectedPath.isEmpty || vm.isScanning || vm.isInstalling || backend.isDevVersion)
                    .help(backend.isDevVersion
                        ? "Online install unavailable for dev builds (\(backend.bundledVersion ?? "unknown")). Use 'from a local file…' instead."
                        : "")
            }
        }
    }
}
