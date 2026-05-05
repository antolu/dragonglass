import Combine
import Foundation
import OSLog

private let logger = Logger(subsystem: subsystem, category: "UpdateChecker")
private let githubReleasesURL = URL(string: "https://api.github.com/repos/antolu/dragonglass/releases/latest")!
private let checkIntervalSeconds: TimeInterval = 86400
private let lastCheckKey = "updateChecker.lastCheckDate"
private let latestVersionKey = "updateChecker.latestVersion"

class UpdateChecker: ObservableObject {
    @Published var latestVersion: String?
    @Published var isChecking = false
    @Published var checkError: String?

    private var periodicTask: Task<Void, Never>?

    func currentVersion() -> String? {
        guard let url = Bundle.main.url(forResource: "version", withExtension: "txt"),
              let v = try? String(contentsOf: url, encoding: .utf8) else { return nil }
        return v.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    func hasUpdate() -> Bool {
        guard let current = currentVersion(), let latest = latestVersion else { return false }
        return isNewerVersion(latest, than: current)
    }

    func startPeriodicChecks(disabled: Bool) {
        periodicTask?.cancel()
        guard !disabled else { return }
        periodicTask = Task {
            await checkIfDue()
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(checkIntervalSeconds))
                await checkIfDue()
            }
        }
    }

    func stopPeriodicChecks() {
        periodicTask?.cancel()
        periodicTask = nil
    }

    func checkNow() {
        Task { await performCheck() }
    }

    private func checkIfDue() async {
        let lastCheck = UserDefaults.standard.object(forKey: lastCheckKey) as? Date
        guard lastCheck == nil || Date().timeIntervalSince(lastCheck!) > checkIntervalSeconds else {
            if let cached = UserDefaults.standard.string(forKey: latestVersionKey) {
                latestVersion = cached
            }
            return
        }
        await performCheck()
    }

    private func performCheck() async {
        isChecking = true
        checkError = nil
        defer { isChecking = false }
        do {
            var request = URLRequest(url: githubReleasesURL)
            request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
            request.timeoutInterval = 10
            let (data, response) = try await URLSession.shared.data(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 200 else {
                checkError = "GitHub API returned non-200"
                return
            }
            guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let tagName = json["tag_name"] as? String else {
                checkError = "Unexpected GitHub API response"
                return
            }
            let version = tagName.hasPrefix("v") ? String(tagName.dropFirst()) : tagName
            latestVersion = version
            UserDefaults.standard.set(version, forKey: latestVersionKey)
            UserDefaults.standard.set(Date(), forKey: lastCheckKey)
            logger.info("latest release: \(version, privacy: .public)")
        } catch {
            checkError = error.localizedDescription
            logger.warning("update check failed: \(error.localizedDescription, privacy: .public)")
        }
    }
}

private func isNewerVersion(_ a: String, than b: String) -> Bool {
    let aParts = a.split(separator: ".").compactMap { Int($0) }
    let bParts = b.split(separator: ".").compactMap { Int($0) }
    let count = max(aParts.count, bParts.count)
    for i in 0..<count {
        let av = i < aParts.count ? aParts[i] : 0
        let bv = i < bParts.count ? bParts[i] : 0
        if av != bv { return av > bv }
    }
    return false
}
