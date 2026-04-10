import SwiftUI

struct EventRow: View {
    let event: AgentEvent
    var detailed: Bool = false
    var includeToolCalls: Bool = false

    var body: some View {
        switch event {
        case .status(let msg):
            Text(msg)
                .font(.caption)
                .foregroundColor(.secondary)
                .italic()
                .textSelection(.enabled)
        case .assistantMessage(let msg):
            Text(LocalizedStringKey(msg))
                .textSelection(.enabled)
        case .mcpTool:
            EmptyView()
        case .config:
            EmptyView()
        case .configAck:
            Text("Settings saved")
                .font(.caption)
                .foregroundColor(.green)
                .textSelection(.enabled)
        case .done:
            Divider()
        case .modelsList:
            EmptyView()
        case .usage:
            EmptyView()
        case .conversationsList:
            EmptyView()
        case .conversationLoaded:
            EmptyView()
        case .userMessage(let msg):
            HStack {
                Spacer()
                Text(msg)
                    .padding(8)
                    .background(Color.accentColor.opacity(0.1))
                    .cornerRadius(8)
                    .textSelection(.enabled)
            }
        case .approvalRequest(let req):
            let row = HStack(spacing: 6) {
                Image(systemName: "pencil.circle")
                    .foregroundColor(.orange)
                Text("Pending approval: \(req.description)")
                    .font(.caption)
                    .foregroundColor(.orange)
            }
            .padding(4)
            .background(Color.orange.opacity(0.08))
            .cornerRadius(4)
            if includeToolCalls {
                row.textSelection(.enabled)
            } else {
                row.textSelection(.disabled)
            }
        case .unknown(let type):
            Text("Unknown event: \(type)")
                .font(.caption)
        }
    }
}
