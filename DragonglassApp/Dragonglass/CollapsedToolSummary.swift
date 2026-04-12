import SwiftUI

struct CollapsedToolSummary: View {
    let turn: ChatTurn
    let events: [AgentEvent]
    var detailed: Bool = false
    var onOpenNote: ((String) -> Void)?
    var includeToolCalls: Bool = false
    @State private var isExpanded = false

    var body: some View {
        if turn.toolCallIndices.isEmpty { return AnyView(EmptyView()) }
        return AnyView(
            DisclosureGroup(isExpanded: $isExpanded) {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(turn.toolCallIndices, id: \.self) { idx in
                        if case .mcpTool(let t, let p, let m, let d) = events[idx] {
                            ToolCallBadge(
                                tool: t,
                                phase: p,
                                message: m,
                                detail: d,
                                detailed: detailed,
                                onOpenNote: onOpenNote,
                                selectable: includeToolCalls
                            )
                        }
                    }
                }
                .padding(.top, 2)
            } label: {
                let count = turn.toolCallIndices.count
                Text("\(count) tool call\(count == 1 ? "" : "s")")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .textSelection(.disabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .contentShape(Rectangle())
                    .onTapGesture { isExpanded.toggle() }
            }
        )
    }
}
