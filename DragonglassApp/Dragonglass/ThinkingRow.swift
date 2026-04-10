import SwiftUI

struct ThinkingRow: View {
    @State private var opMessage: String = "Thinking"

    var body: some View {
        HStack {
            if #available(macOS 14.0, *) {
                Image(systemName: "sparkles")
                    .symbolEffect(.pulse)
            } else {
                Image(systemName: "sparkles")
            }
            Text(opMessage)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(8)
        .background(Color.secondary.opacity(0.1))
        .cornerRadius(8)
    }
}
