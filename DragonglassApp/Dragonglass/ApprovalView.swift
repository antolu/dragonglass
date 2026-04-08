import SwiftUI

struct DiffView: View {
    let diff: String

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(Array(diff.components(separatedBy: "\n").enumerated()), id: \.offset) { _, line in
                Text(line.isEmpty ? " " : line)
                    .font(.system(.caption, design: .monospaced))
                    .foregroundColor(lineColor(line))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(lineBackground(line))
            }
        }
    }

    private func lineColor(_ line: String) -> Color {
        if line.hasPrefix("+") { return .green }
        if line.hasPrefix("-") { return .red }
        if line.hasPrefix("@") { return .blue }
        return .primary
    }

    private func lineBackground(_ line: String) -> Color {
        if line.hasPrefix("+") { return Color.green.opacity(0.08) }
        if line.hasPrefix("-") { return Color.red.opacity(0.08) }
        return .clear
    }
}

struct ApprovalView: View {
    @EnvironmentObject var client: AgentClient
    let request: ApprovalRequest

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Approve Edit?")
                .font(.headline)

            Text(request.description)
                .font(.subheadline)
                .foregroundColor(.secondary)

            if !request.diff.isEmpty {
                ScrollView {
                    DiffView(diff: request.diff)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(maxHeight: 200)
                .background(Color(NSColor.textBackgroundColor))
                .cornerRadius(6)
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(Color.secondary.opacity(0.3), lineWidth: 1)
                )
            }

            HStack {
                Button("Reject") {
                    client.rejectRequest(request)
                }
                .foregroundColor(.red)

                Spacer()

                Button("Approve for Session") {
                    client.approveRequest(request, forSession: true)
                }

                Button("Approve") {
                    client.approveRequest(request, forSession: false)
                }
                .buttonStyle(.borderedProminent)
            }
        }
        .padding()
        .frame(width: 420, height: 340)
    }
}
