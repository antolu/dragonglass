import SwiftUI

struct ToolCallBadge: View {
    let tool: String
    let phase: String
    let message: String
    let detail: String
    var detailed: Bool = false
    var onOpenNote: ((String) -> Void)?
    var selectable: Bool = false
    @State private var showingDetail = false

    private var toolPhase: ToolPhase { ToolPhase(rawValue: phase) }

    private var notePath: String? {
        guard tool == "dragonglass_read_note_with_hash",
              toolPhase == .done,
              message.hasPrefix("Reading: ") else { return nil }
        return String(message.dropFirst("Reading: ".count))
    }

    private var badgeColor: Color {
        switch toolPhase {
        case .error: return .red
        case .validationError: return .orange
        default: return .blue
        }
    }

    private var isErrorLike: Bool {
        toolPhase == .error || toolPhase == .validationError
    }

    private var badgeLabel: String {
        switch toolPhase {
        case .error: return "\(tool): error"
        case .validationError: return "\(tool): validation error"
        default: return message
        }
    }

    var body: some View {
        let badge = HStack(alignment: .top, spacing: 6) {
            if toolPhase == .error {
                Image(systemName: "exclamationmark.circle")
                    .foregroundColor(.red)
            } else if toolPhase == .validationError {
                Image(systemName: "exclamationmark.triangle")
                    .foregroundColor(.orange)
            }
            if detailed {
                VStack(alignment: .leading, spacing: 2) {
                    Text("\(tool) [\(phase)]")
                        .foregroundColor(.secondary)
                    Text(message + (detail.isEmpty ? "" : " — \(detail)"))
                }
            } else {
                Text(badgeLabel)
            }
        }
        .font(.caption)
        .padding(4)
        .background(badgeColor.opacity(0.08))
        .cornerRadius(4)
        .onTapGesture {
            if isErrorLike {
                showingDetail = true
            } else if let path = notePath {
                onOpenNote?(path)
            }
        }
        .popover(isPresented: $showingDetail) {
            ScrollView {
                Text(detail.isEmpty ? "No detail available." : detail)
                    .font(.caption)
                    .padding()
                    .frame(maxWidth: 320, alignment: .leading)
            }
            .frame(maxHeight: 200)
        }
        if selectable {
            badge.textSelection(.enabled)
        } else {
            badge.textSelection(.disabled)
        }
    }
}
