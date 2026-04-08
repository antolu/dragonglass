import SwiftUI

enum ToolPhase: String {
    case done = "done"
    case error = "error"
    case validationError = "validation_error"
    case unknown

    init(rawValue: String) {
        switch rawValue {
        case "done": self = .done
        case "error": self = .error
        case "validation_error": self = .validationError
        default: self = .unknown
        }
    }
}

struct BottomVisibilityKey: PreferenceKey {
    static let defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}
