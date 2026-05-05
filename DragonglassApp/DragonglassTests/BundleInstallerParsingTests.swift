import XCTest
@testable import Dragonglass

final class BundleInstallerParsingTests: XCTestCase {

    // MARK: - parseProgressEvent

    func testParseProgressEvent_validProgress() throws {
        let data = #"{"type":"progress","message":"Downloading...","fraction":0.4}"#.data(using: .utf8)!
        let event = parseProgressEvent(data)
        guard case .progress(let message, let fraction) = event else {
            XCTFail("expected .progress, got \(String(describing: event))")
            return
        }
        XCTAssertEqual(message, "Downloading...")
        XCTAssertEqual(fraction, 0.4, accuracy: 0.001)
    }

    func testParseProgressEvent_validDone() throws {
        let data = #"{"type":"done"}"#.data(using: .utf8)!
        let event = parseProgressEvent(data)
        guard case .done = event else {
            XCTFail("expected .done, got \(String(describing: event))")
            return
        }
    }

    func testParseProgressEvent_validError() throws {
        let data = #"{"type":"error","message":"SHA256 mismatch"}"#.data(using: .utf8)!
        let event = parseProgressEvent(data)
        guard case .error(let message) = event else {
            XCTFail("expected .error, got \(String(describing: event))")
            return
        }
        XCTAssertEqual(message, "SHA256 mismatch")
    }

    func testParseProgressEvent_unknownType_returnsNil() {
        let data = #"{"type":"unknown","message":"foo"}"#.data(using: .utf8)!
        XCTAssertNil(parseProgressEvent(data))
    }

    func testParseProgressEvent_malformedJSON_returnsNil() {
        let data = "not json at all".data(using: .utf8)!
        XCTAssertNil(parseProgressEvent(data))
    }

    func testParseProgressEvent_emptyData_returnsNil() {
        XCTAssertNil(parseProgressEvent(Data()))
    }

    func testParseProgressEvent_missingTypeField_returnsNil() {
        let data = #"{"message":"foo","fraction":0.5}"#.data(using: .utf8)!
        XCTAssertNil(parseProgressEvent(data))
    }

    func testParseProgressEvent_errorWithMissingMessage_usesDefault() {
        let data = #"{"type":"error"}"#.data(using: .utf8)!
        let event = parseProgressEvent(data)
        guard case .error(let message) = event else {
            XCTFail("expected .error")
            return
        }
        XCTAssertEqual(message, "unknown error")
    }

    // MARK: - Buffer line-splitting logic

    func testBufferLineSplitting_multipleCompleteLines() {
        let input = "{\"type\":\"progress\",\"message\":\"A\",\"fraction\":0.1}\n{\"type\":\"done\"}\n"
        var buffer = input.data(using: .utf8)!
        var events: [BundleProgressEvent] = []

        while let newline = buffer.firstIndex(of: UInt8(ascii: "\n")) {
            let lineData = buffer[buffer.startIndex..<newline]
            buffer = buffer[buffer.index(after: newline)...]
            if let event = parseProgressEvent(lineData) {
                events.append(event)
            }
        }

        XCTAssertEqual(events.count, 2)
        guard case .progress(let msg, _) = events[0] else {
            XCTFail("first event should be progress"); return
        }
        XCTAssertEqual(msg, "A")
        guard case .done = events[1] else {
            XCTFail("second event should be done"); return
        }
    }

    func testBufferLineSplitting_partialLine_notEmitted() {
        let input = "{\"type\":\"progress\",\"message\":\"partial\""
        var buffer = input.data(using: .utf8)!
        var events: [BundleProgressEvent] = []

        while let newline = buffer.firstIndex(of: UInt8(ascii: "\n")) {
            let lineData = buffer[buffer.startIndex..<newline]
            buffer = buffer[buffer.index(after: newline)...]
            if let event = parseProgressEvent(lineData) {
                events.append(event)
            }
        }

        XCTAssertTrue(events.isEmpty, "partial line should not produce an event")
        XCTAssertFalse(buffer.isEmpty, "partial line should remain in buffer")
    }
}
