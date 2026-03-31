import SwiftUI

struct ContentView: View {
    @EnvironmentObject var backend: BackendManager
    @EnvironmentObject var client: AgentClient
    @EnvironmentObject var sttManager: STTManager
    @EnvironmentObject var hotkeyManager: HotkeyManager
    @State private var inputText = ""
    @State private var showingSettings = false
    @State private var showingCustomModel = false
    @State private var customModelText = ""
    @State private var lastModelSent: String?
    @State private var lastRequestStartIndex: Int?
    @State private var showingConversations = false
    @State private var isAtBottom = true
    @State private var escapeMonitor: Any?

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
        .sheet(item: $client.pendingApproval) { req in
            ApprovalView(request: req)
                .environmentObject(client)
        }
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
                    .environmentObject(sttManager)
                    .environmentObject(hotkeyManager)
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
                if case .needsPluginUpdate = phase { return true }
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
            case .needsPluginUpdate(let from, let to):
                Image(systemName: "arrow.triangle.2.circlepath")
                    .font(.largeTitle)
                    .foregroundColor(.orange)
                Text("A plugin update is available (\(from) → \(to)). Update now?")
                    .multilineTextAlignment(.center)
                    .padding()
                Button("Update Plugin") {
                    backend.applyPluginUpdate()
                }
                .buttonStyle(.borderedProminent)
            case .needsPluginReload:
                Image(systemName: "checkmark.circle")
                    .font(.largeTitle)
                    .foregroundColor(.green)
                Text("Plugin updated. Toggle it off and on in Obsidian → Settings → Community plugins to apply.")
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
                        EventRow(event: client.events[index], detailed: client.detailedToolEvents)
                    }

                    ForEach(client.turns) { turn in
                        EventRow(event: client.events[turn.userMessageIndex], detailed: client.detailedToolEvents)

                        if turn.isCompleted {
                            CollapsedToolSummary(turn: turn, events: client.events, detailed: client.detailedToolEvents, onOpenNote: { client.openNote(path: $0) })
                            if let doneIdx = turn.doneIndex {
                                EventRow(event: client.events[doneIdx], detailed: client.detailedToolEvents)
                            }
                        } else {
                            if let idx = turn.toolCallIndices.last,
                               case .mcpTool(let t, let p, let m, let d) = client.events[idx] {
                                ToolCallBadge(tool: t, phase: p, message: m, detail: d, detailed: client.detailedToolEvents, onOpenNote: { client.openNote(path: $0) })
                                    .id(idx)
                                    .transition(.asymmetric(
                                        insertion: .move(edge: .bottom).combined(with: .opacity),
                                        removal: .move(edge: .top).combined(with: .opacity)
                                    ))
                            }
                        }

                        if let aIdx = turn.assistantMessageIndex {
                            EventRow(event: client.events[aIdx], detailed: client.detailedToolEvents)
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
            TextField(sttPendingPrompt, text: $inputText)
                .textFieldStyle(.plain)
                .onSubmit(sendMessage)
                .disabled(client.isThinking)

            MicButton()
                .environmentObject(sttManager)
                .environmentObject(client)

            if client.isThinking && client.pendingApproval == nil {
                Button(action: { client.stopChat() }) {
                    Image(systemName: "stop.fill")
                        .font(.body)
                        .foregroundColor(.red)
                        .frame(width: 30, height: 30)
                        .background(Color.red.opacity(0.1))
                        .cornerRadius(4)
                }
                .buttonStyle(.plain)
            } else if !client.isThinking {
                Button(action: sendMessage) {
                    Image(systemName: "paperplane.fill")
                }
                .disabled(inputText.isEmpty || backend.phase != .ready)
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .onChange(of: sttManager.pendingText) { _, text in
            if let text { inputText = text }
        }
        .onChange(of: sttManager.readyToFire) { _, ready in
            guard ready, let text = sttManager.pendingText, !text.isEmpty else { return }
            sttManager.clearFireFlag()
            let toSend = text
            inputText = ""
            sendSTT(toSend)
        }
        .onAppear { installEscapeMonitor() }
        .onDisappear { removeEscapeMonitor() }
    }

    private var sttPendingPrompt: String {
        if sttManager.isRecording { return "Recording…" }
        if sttManager.isTranscribing { return "Transcribing…" }
        if sttManager.pendingText != nil { return "Press Esc to cancel" }
        return "Ask anything..."
    }

    private func sendSTT(_ text: String) {
        guard !text.isEmpty, !client.isThinking else { return }
        if !client.isConnected { client.connect() }
        let model = client.selectedModel.isEmpty ? nil : client.selectedModel
        lastModelSent = model
        lastRequestStartIndex = client.events.count
        client.sendChat(text: text, model: model)
    }

    private func installEscapeMonitor() {
        escapeMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { event in
            if event.keyCode == 53 && self.sttManager.pendingText != nil {
                self.sttManager.cancelPending()
                self.inputText = ""
                return nil
            }
            return event
        }
    }

    private func removeEscapeMonitor() {
        if let mon = escapeMonitor {
            NSEvent.removeMonitor(mon)
            escapeMonitor = nil
        }
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
            case .mcpTool(_, let phase, _, _) where ToolPhase(rawValue: phase) == .error || ToolPhase(rawValue: phase) == .validationError:
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
        case .mcpTool:
            EmptyView()
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
        case .approvalRequest(let req):
            HStack(spacing: 6) {
                Image(systemName: "pencil.circle")
                    .foregroundColor(.orange)
                Text("Pending approval: \(req.description)")
                    .font(.caption)
                    .foregroundColor(.orange)
            }
            .padding(4)
            .background(Color.orange.opacity(0.08))
            .cornerRadius(4)
        case .unknown(let type):
            Text("Unknown event: \(type)")
                .font(.caption)
        }
    }
}

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

struct ToolCallBadge: View {
    let tool: String
    let phase: String
    let message: String
    let detail: String
    var detailed: Bool = false
    var onOpenNote: ((String) -> Void)?
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
        HStack(alignment: .top, spacing: 6) {
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
    }
}

struct CollapsedToolSummary: View {
    let turn: ChatTurn
    let events: [AgentEvent]
    var detailed: Bool = false
    var onOpenNote: ((String) -> Void)?
    @State private var isExpanded = false

    var body: some View {
        if turn.toolCallIndices.isEmpty { return AnyView(EmptyView()) }
        return AnyView(
            DisclosureGroup(isExpanded: $isExpanded) {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(turn.toolCallIndices, id: \.self) { idx in
                        if case .mcpTool(let t, let p, let m, let d) = events[idx] {
                            ToolCallBadge(tool: t, phase: p, message: m, detail: d, detailed: detailed, onOpenNote: onOpenNote)
                        }
                    }
                }
                .padding(.top, 2)
            } label: {
                let count = turn.toolCallIndices.count
                Text("\(count) tool call\(count == 1 ? "" : "s")")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        )
    }
}

private struct BottomVisibilityKey: PreferenceKey {
    static let defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}

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

struct MicButton: View {
    @EnvironmentObject var sttManager: STTManager
    @EnvironmentObject var client: AgentClient
    @State private var isHolding = false
    @State private var pulsing = false

    var body: some View {
        ZStack {
            if sttManager.isRecording {
                Circle()
                    .fill(Color.red.opacity(0.25))
                    .scaleEffect(pulsing ? 1.5 : 1.0)
                    .animation(.easeInOut(duration: 0.7).repeatForever(autoreverses: true), value: pulsing)
                    .frame(width: 30, height: 30)
                    .onAppear { pulsing = true }
                    .onDisappear { pulsing = false }
            }
            if sttManager.isTranscribing {
                ProgressView()
                    .scaleEffect(0.6)
                    .frame(width: 30, height: 30)
            } else {
                Image(systemName: sttManager.isRecording ? "microphone.fill" : "microphone")
                    .foregroundColor(sttManager.isRecording ? .red : .secondary)
                    .frame(width: 30, height: 30)
            }
        }
        .gesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in
                    guard !isHolding else { return }
                    isHolding = true
                    sttManager.startRecording()
                }
                .onEnded { _ in
                    guard isHolding else { return }
                    isHolding = false
                    sttManager.stopAndTranscribe()
                }
        )
        .disabled(!sttManager.micPermissionGranted || !sttManager.isModelReady || client.isThinking)
        .opacity(sttManager.micPermissionGranted && sttManager.isModelReady ? 1.0 : 0.3)
        .help(
            !sttManager.micPermissionGranted ? "Microphone permission required" :
            !sttManager.isModelReady ? "Download a Whisper model in Settings first" :
            "Hold to dictate"
        )
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
