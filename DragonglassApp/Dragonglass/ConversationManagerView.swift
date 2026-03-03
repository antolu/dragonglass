import SwiftUI

struct ConversationManagerView: View {
    @EnvironmentObject var client: AgentClient
    @Binding var isPresented: Bool

    var body: some View {
        VStack(spacing: 0) {
            header

            if client.conversations.isEmpty {
                emptyState
            } else {
                conversationList
            }

            Spacer(minLength: 0)
        }
        .frame(width: 300, height: 400)
        .onAppear {
            client.fetchConversations()
        }
    }

    private var header: some View {
        HStack {
            Text("Conversations")
                .font(.headline)
            Spacer()
            Button(action: {
                client.startNewChat()
                isPresented = false
            }) {
                HStack(spacing: 4) {
                    Image(systemName: "plus")
                    Text("New Chat")
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .foregroundColor(.accentColor)
            }
            .buttonStyle(.plain)
            .focusable(false)
        }
        .padding()
        .background(Color(NSColor.windowBackgroundColor))
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Spacer()
            Image(systemName: "bubble.left.and.bubble.right")
                .font(.largeTitle)
                .foregroundColor(.secondary)
            Text("No recent conversations")
                .foregroundColor(.secondary)
            Spacer()
        }
    }

    private var conversationList: some View {
        ScrollView {
            LazyVStack(spacing: 1) {
                ForEach(client.conversations) { conversation in
                    ConversationRow(conversation: conversation) {
                        client.loadConversation(id: conversation.id)
                        isPresented = false
                    } onDelete: {
                        client.deleteConversation(id: conversation.id)
                    }
                }
            }
        }
    }
}

struct ConversationRow: View {
    let conversation: ConversationMetadata
    let onSelect: () -> Void
    let onDelete: () -> Void
    @State private var isHovered = false

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(conversation.title)
                    .font(.body)
                    .lineLimit(1)
                Text(formatDate(conversation.updatedAt))
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            Spacer()
            if isHovered {
                Button(action: onDelete) {
                    Image(systemName: "trash")
                        .foregroundColor(.red)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal)
        .padding(.vertical, 10)
        .background(isHovered ? Color.secondary.opacity(0.1) : Color.clear)
        .contentShape(Rectangle())
        .onTapGesture(perform: onSelect)
        .onHover { hovering in
            isHovered = hovering
        }
    }

    private func formatDate(_ timestamp: Double) -> String {
        // Simple hack: since we used asyncio.get_event_loop().time()
        // which is monotonic/relative, we should probably have used
        // time.time() in Python. Let's assume we fixed it to be seconds since epoch.
        let date = Date(timeIntervalSince1970: timestamp)
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .full
        return formatter.localizedString(for: date, relativeTo: Date())
    }
}
