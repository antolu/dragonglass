import SwiftUI

struct ContentView: View {
    @EnvironmentObject var backend: BackendManager
    @EnvironmentObject var client: AgentClient
    @State private var inputText = ""
    @State private var showingSettings = false
    @State private var showingCustomModel = false
    @State private var customModelText = ""
    @State private var lastModelSent: String?
    @State private var lastRequestStartIndex: Int?
    @State private var showingConversations = false
    @State private var isAtBottom = true

    var body: some View {
        VStack(spacing: 0) {
            header

            if backend.phase != .ready {
                statusView
            } else {
                chatView
            }

            inputArea
        }
        .frame(width: 400, height: 500)
    }

    private var header: some View {
        HStack {
            modelPicker
            Spacer()

            Button(action: {
                guard !client.isThinking else { return }
                client.startNewChat()
            }) {
                Image(systemName: "square.and.pencil")
            }
            .buttonStyle(.plain)
            .focusable(false)
            .disabled(client.isThinking)

            Button(action: {
                guard !client.isThinking else { return }
                showingSettings = false
                showingConversations = true
            }) {
                Image(systemName: "bubble.left.and.bubble.right")
            }
            .buttonStyle(.plain)
            .focusable(false)
            .disabled(client.isThinking)
            .popover(isPresented: $showingConversations, arrowEdge: .top) {
                ConversationManagerView(isPresented: $showingConversations)
                    .environmentObject(client)
            }

            Button(action: {
                guard !client.isThinking else { return }
                showingConversations = false
                showingSettings = true
            }) {
                Image(systemName: "gear")
            }
            .buttonStyle(.plain)
            .focusable(false)
            .disabled(client.isThinking)
            .popover(isPresented: $showingSettings, arrowEdge: .top) {
                SettingsView(isPresented: $showingSettings)
                    .environmentObject(client)
            }
        }
        .padding()
        .background(Color(NSColor.windowBackgroundColor))
        .onAppear {
            if backend.phase == .ready {
                if !client.isConnected { client.connect() }
                client.refreshState()
            }
        }
        .onChange(of: backend.phase) { _, phase in
            if phase == .ready || ({
                if case .needsPluginReload = phase { return true }
                return false
            }()) {
                if !client.isConnected { client.connect() }
                client.refreshState()
            }
        }
    }

    private var modelPicker: some View {
        Menu {
            Button("Default") {
                client.setSelectedModel("")
            }

            if !client.availableModels.isEmpty {
                Divider()
                Text(client.llmBackend == "opencode" ? "OpenCode Models" : "Ollama Models")
                ForEach(client.availableModels, id: \.self) { model in
                    Button(model) {
                        client.setSelectedModel(model)
                    }
                }
            }

            if !client.extraModels.isEmpty {
                Divider()
                Text("Extra Models")
                ForEach(client.extraModels, id: \.self) { model in
                    Button(model) {
                        client.setSelectedModel(model)
                    }
                }
            }

            Divider()
            Button("Custom...") {
                customModelText = client.selectedModel
                showingCustomModel = true
            }
        } label: {
            HStack(spacing: 4) {
                Text(client.selectedModel.isEmpty ? "Default" : client.selectedModel)
                    .lineLimit(1)
                Image(systemName: "chevron.up.chevron.down")
                    .font(.caption2)
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Color.secondary.opacity(0.1))
            .cornerRadius(4)
        }
        .fixedSize()
        .popover(isPresented: $showingCustomModel) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Custom Model Name")
                    .font(.caption)
                    .bold()
                TextField("e.g. gpt-4", text: $customModelText)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        let trimmedModel = customModelText.trimmingCharacters(in: .whitespacesAndNewlines)
                        if !trimmedModel.isEmpty {
                            client.setSelectedModel(trimmedModel)
                        }
                        showingCustomModel = false
                    }
                Button("Set Model") {
                    let trimmedModel = customModelText.trimmingCharacters(in: .whitespacesAndNewlines)
                    if !trimmedModel.isEmpty {
                        client.setSelectedModel(trimmedModel)
                    }
                    showingCustomModel = false
                }
                .buttonStyle(.borderedProminent)
            }
            .padding()
            .frame(width: 200)
        }
    }

    private var statusView: some View {
        VStack {
            Spacer()
            switch backend.phase {
            case .installing:
                ProgressView("Installing dependencies...")
            case .starting:
                ProgressView("Starting backend...")
            case .needsPluginReload(let message):
                Image(systemName: "arrow.triangle.2.circlepath")
                    .font(.largeTitle)
                    .foregroundColor(.orange)
                Text(message)
                    .multilineTextAlignment(.center)
                    .padding()
                Button("Done") {
                    backend.phase = .ready
                }
                .buttonStyle(.borderedProminent)
            case .failed(let error):
                Image(systemName: "exclamationmark.triangle")
                    .font(.largeTitle)
                    .foregroundColor(.red)
                Text(error)
                    .multilineTextAlignment(.center)
                    .padding()
                Button("Retry") {
                    Task { await backend.startBackend() }
                }
            default:
                EmptyView()
            }
            Spacer()
        }
    }

    private var chatView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(0..<client.events.count, id: \.self) { index in
                        EventRow(event: client.events[index], detailed: client.detailedToolEvents)
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
                if let last = client.events.indices.last {
                    if isAtBottom {
                        proxy.scrollTo("bottom")
                    }

                    if case .done = client.events[last],
                       let model = lastModelSent,
                       !model.isEmpty,
                       !client.availableModels.contains(model),
                       !client.extraModels.contains(model),
                       shouldPersistCustomModel(completedEventIndex: last) {
                        client.saveModel(model)
                    }
                    lastModelSent = nil
                    lastRequestStartIndex = nil
                }
            }
        }
    }

    private var inputArea: some View {
        HStack {
            TextField("Ask anything...", text: $inputText)
                .textFieldStyle(.plain)
                .onSubmit(sendMessage)
                .disabled(client.isThinking)

            if client.isThinking {
                Button(action: { client.stopChat() }) {
                    Image(systemName: "stop.fill")
                        .font(.body)
                        .foregroundColor(.red)
                        .frame(width: 30, height: 30)
                        .background(Color.red.opacity(0.1))
                        .cornerRadius(4)
                }
                .buttonStyle(.plain)
            } else {
                Button(action: sendMessage) {
                    Image(systemName: "paperplane.fill")
                }
                .disabled(inputText.isEmpty || backend.phase != .ready)
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
    }

    private func sendMessage() {
        guard !inputText.isEmpty else { return }
        if !client.isConnected { client.connect() }

        let model = client.selectedModel.isEmpty ? nil : client.selectedModel
        lastModelSent = model
        lastRequestStartIndex = client.events.count

        client.sendChat(text: inputText, model: model)
        inputText = ""
    }

    private func shouldPersistCustomModel(completedEventIndex: Int) -> Bool {
        guard let startIndex = lastRequestStartIndex,
              startIndex <= completedEventIndex,
              startIndex >= 0,
              completedEventIndex < client.events.count else {
            return false
        }

        var hasText = false
        for event in client.events[startIndex...completedEventIndex] {
            switch event {
            case .assistantMessage(let msg):
                if !msg.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    hasText = true
                }
            case .error:
                return false
            case .status(let message):
                if message.lowercased().hasPrefix("error:") {
                    return false
                }
            default:
                break
            }
        }

        return hasText
    }
}

struct EventRow: View {
    let event: AgentEvent
    var detailed: Bool = false

    var body: some View {
        switch event {
        case .status(let msg):
            Text(msg)
                .font(.caption)
                .foregroundColor(.secondary)
                .italic()
        case .assistantMessage(let msg):
            Text(LocalizedStringKey(msg))
        case .error(let tool, let err):
            Text("\(tool): \(err)")
                .foregroundColor(.red)
        case .mcpTool(let tool, let phase, let message, let detail):
            HStack(alignment: .top, spacing: 6) {
                if phase == "error" {
                    Image(systemName: "exclamationmark.circle")
                        .foregroundColor(.red)
                }
                if detailed {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("\(tool) [\(phase)]")
                            .foregroundColor(.secondary)
                        Text(message + (detail.isEmpty ? "" : " — \(detail)"))
                    }
                } else {
                    Text(message)
                }
            }
            .font(.caption)
            .padding(4)
            .background(phase == "error" ? Color.red.opacity(0.08) : Color.orange.opacity(0.08))
            .cornerRadius(4)
        case .config:
            EmptyView()
        case .configAck:
            Text("Settings saved")
                .font(.caption)
                .foregroundColor(.green)
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
            }
        case .unknown(let type):
            Text("Unknown event: \(type)")
                .font(.caption)
        }
    }
}

private struct BottomVisibilityKey: PreferenceKey {
    static let defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}

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
