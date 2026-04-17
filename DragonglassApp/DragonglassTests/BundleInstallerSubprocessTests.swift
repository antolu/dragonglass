import XCTest

/// Subprocess integration tests — excluded from the default test plan.
/// Run via: xcodebuild test -testPlan BundleIntegration
final class BundleInstallerSubprocessTests: XCTestCase {

    private var repoRoot: String {
        var url = URL(fileURLWithPath: #file)
        while url.path != "/" {
            url = url.deletingLastPathComponent()
            if FileManager.default.fileExists(atPath: url.appendingPathComponent("pyproject.toml").path) {
                return url.path
            }
        }
        return ""
    }

    private func runBundle(_ args: [String]) -> (output: String, exitCode: Int32) {
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        proc.arguments = ["-m", "dragonglass.bundle"] + args

        var env = ProcessInfo.processInfo.environment
        env["PYTHONPATH"] = repoRoot
        proc.environment = env

        let pipe = Pipe()
        proc.standardOutput = pipe
        proc.standardError = Pipe()

        try? proc.run()
        proc.waitUntilExit()

        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        let output = String(data: data, encoding: .utf8) ?? ""
        return (output, proc.terminationStatus)
    }

    func testInfo_exitCodeZero_andValidJSON() throws {
        let (output, exitCode) = runBundle(["info"])
        XCTAssertEqual(exitCode, 0, "python3 -m dragonglass.bundle info should exit 0")

        let trimmed = output.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let data = trimmed.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            XCTFail("stdout is not valid JSON: \(trimmed)")
            return
        }

        XCTAssertNotNil(json["os"], "JSON should have 'os' key")
        XCTAssertNotNil(json["arch"], "JSON should have 'arch' key")
        XCTAssertNotNil(json["python"], "JSON should have 'python' key")
        XCTAssertEqual(json["os"] as? String, "darwin", "os should be darwin on macOS")
    }

    func testVerify_nonexistentFile_returnsErrorJSON_andNonzeroExit() throws {
        let (output, exitCode) = runBundle(["verify", "/nonexistent/path/bundle.tar.gz"])
        XCTAssertNotEqual(exitCode, 0, "verify of nonexistent file should exit nonzero")

        let lines = output.split(separator: "\n").filter { !$0.isEmpty }
        guard let lastLine = lines.last,
              let data = String(lastLine).data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            XCTFail("last stdout line is not valid JSON")
            return
        }
        XCTAssertEqual(json["type"] as? String, "error")
    }
}
