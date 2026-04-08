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
    @State private var shiftMonitor: Any?
    @State private var includeToolCallsInSelection = false

    var body: some View {
        VStack(spacing: 0) {
            header

            if backend.phase != .ready {
                statusView
            } else {
                ChatTimelineView(
                    includeToolCallsInSelection: includeToolCallsInSelection,
                    isAtBottom: $isAtBottom,
                    onEventsChanged: handleEventsChanged,
                    onResend: { msg in inputText = msg }
                )
                .environmentObject(client)
                .environmentObject(backend)
            }

            InputBarView(
                inputText: $inputText,
                onSend: sendMessage,
                onSTT: sendSTT
            )
            .environmentObject(client)
            .environmentObject(sttManager)
            .environmentObject(backend)
            .onAppear { installEscapeMonitor() }
            .onDisappear { removeEscapeMonitor() }
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
            .disabled(client.isThinking || client.turns.isEmpty)

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

    private func handleEventsChanged() {
        guard let last = client.events.indices.last else { return }
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
            if event.keyCode == 53 && (self.sttManager.isRecording || self.sttManager.pendingText != nil) {
                if self.sttManager.isRecording {
                    self.sttManager.cancelRecording()
                }
                self.sttManager.cancelPending()
                self.inputText = ""
                return nil
            }
            return event
        }

        shiftMonitor = NSEvent.addLocalMonitorForEvents(matching: [.flagsChanged, .leftMouseDown, .leftMouseDragged, .leftMouseUp]) { event in
            self.includeToolCallsInSelection = event.modifierFlags.contains(.shift)
            return event
        }
    }

    private func removeEscapeMonitor() {
        if let mon = escapeMonitor {
            NSEvent.removeMonitor(mon)
            escapeMonitor = nil
        }
        if let mon = shiftMonitor {
            NSEvent.removeMonitor(mon)
            shiftMonitor = nil
        }
        includeToolCallsInSelection = false
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
