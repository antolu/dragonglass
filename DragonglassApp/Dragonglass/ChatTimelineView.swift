import SwiftUI

struct ChatTimelineView: View {
    @EnvironmentObject var client: AgentClient
    @EnvironmentObject var backend: BackendManager
    let includeToolCallsInSelection: Bool
    @Binding var isAtBottom: Bool
    let onEventsChanged: () -> Void
    @Binding var inputText: String

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    if let warning = backend.obsidianWarning {
                        HStack(spacing: 6) {
                            Image(systemName: "exclamationmark.triangle")
                                .foregroundColor(.orange)
                                .font(.caption)
                            Text(warning)
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        .padding(8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.orange.opacity(0.08))
                        .cornerRadius(6)
                    }
                    ForEach(client.prefixEventIndices, id: \.self) { index in
                        EventRow(event: client.events[index], detailed: client.detailedToolEvents, includeToolCalls: includeToolCallsInSelection)
                    }

                    ForEach(client.turns) { turn in
                        if !turn.isCompleted, case .userMessage(let msg) = client.events[turn.userMessageIndex] {
                            HStack(alignment: .top, spacing: 4) {
                                Button(action: { inputText = msg }) {
                                    Image(systemName: "arrow.counterclockwise")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                        .padding(4)
                                }
                                .buttonStyle(.plain)
                                .help("Resend message")
                                EventRow(event: client.events[turn.userMessageIndex], detailed: client.detailedToolEvents, includeToolCalls: includeToolCallsInSelection)
                            }
                        } else {
                            EventRow(event: client.events[turn.userMessageIndex], detailed: client.detailedToolEvents, includeToolCalls: includeToolCallsInSelection)
                        }

                        if turn.isCompleted {
                            CollapsedToolSummary(
                                turn: turn,
                                events: client.events,
                                detailed: client.detailedToolEvents,
                                onOpenNote: { client.openNote(path: $0) },
                                includeToolCalls: includeToolCallsInSelection
                            )
                            if let doneIdx = turn.doneIndex {
                                EventRow(event: client.events[doneIdx], detailed: client.detailedToolEvents, includeToolCalls: includeToolCallsInSelection)
                            }
                        } else {
                            if let idx = turn.toolCallIndices.last,
                               case .mcpTool(let t, let p, let m, let d) = client.events[idx] {
                                ToolCallBadge(
                                    tool: t,
                                    phase: p,
                                    message: m,
                                    detail: d,
                                    detailed: client.detailedToolEvents,
                                    onOpenNote: { client.openNote(path: $0) },
                                    selectable: includeToolCallsInSelection
                                )
                                    .id(idx)
                                    .transition(.asymmetric(
                                        insertion: .move(edge: .bottom).combined(with: .opacity),
                                        removal: .move(edge: .top).combined(with: .opacity)
                                    ))
                            }
                        }

                        if let aIdx = turn.assistantMessageIndex {
                            EventRow(event: client.events[aIdx], detailed: client.detailedToolEvents, includeToolCalls: includeToolCallsInSelection)
                        }
                    }

                    if client.isThinking {
                        ThinkingRow()
                    }
                }
                .padding()

                GeometryReader { geo in
                    Color.clear.preference(
                        key: BottomVisibilityKey.self,
                        value: geo.frame(in: .global).minY
                    )
                }
                .frame(height: 1)
                .id("bottom")
            }
            .coordinateSpace(name: "scroll")
            .backgroundPreferenceValue(BottomVisibilityKey.self) { minY in
                GeometryReader { scrollGeo in
                    let scrollMaxY = scrollGeo.frame(in: .global).maxY
                    Color.clear.onAppear {
                        isAtBottom = minY <= scrollMaxY
                    }.onChange(of: minY) { _, y in
                        isAtBottom = y <= scrollMaxY
                    }
                }
            }
            .onChange(of: client.events.count) { _, _ in
                withAnimation(.easeInOut(duration: 0.3)) {}
                if isAtBottom {
                    proxy.scrollTo("bottom")
                }
                onEventsChanged()
            }
        }
    }
}
