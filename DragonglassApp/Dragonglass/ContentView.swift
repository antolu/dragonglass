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

    var body: some View {
        ZStack(alignment: .trailing) {
            // Main Chat UI
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

            // Overlay and Settings Pane
            if showingSettings {
                Color.black.opacity(0.1)
                    .contentShape(Rectangle())
                    .onTapGesture {
                        showingSettings = false
                    }

                SettingsView(isPresented: $showingSettings)
                    .environmentObject(client)
                    .background(Color(NSColor.windowBackgroundColor))
                    .transition(.move(edge: .trailing))
            }
        }
        .frame(width: 400, height: 500)
        .animation(.easeInOut(duration: 0.2), value: showingSettings)
    }

    private var header: some View {
        HStack {
            modelPicker
            Spacer()
            Button(action: { showingSettings = true }) {
                Image(systemName: "gear")
            }
            .buttonStyle(.plain)
            .focusable(false)
        }
        .padding()
        .background(Color(NSColor.windowBackgroundColor))
        .onAppear {
            if backend.phase == .ready {
                if !client.isConnected { client.connect() }
                client.refreshState()
            }
        }
        .onChange(of: backend.phase) { phase in
            if phase == .ready {
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
                Text("Ollama Models")
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
                        EventRow(event: client.events[index])
                    }

                    if client.isThinking {
                        ThinkingRow()
                    }
                }
                .padding()
            }
            .onChange(of: client.events.count) { _ in
                if let last = client.events.indices.last {
                    proxy.scrollTo(last)

                    // If last event is .done and we used a custom model, save it
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

            Button(action: sendMessage) {
                Image(systemName: "paperplane.fill")
            }
            .disabled(inputText.isEmpty || backend.phase != .ready)
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
            case .text(let chunk):
                if !chunk.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
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

    var body: some View {
        switch event {
        case .status(let msg):
            Text(msg)
                .font(.caption)
                .foregroundColor(.secondary)
                .italic()
        case .text(let chunk):
            Text(chunk)
        case .error(let tool, let err):
            Text("\(tool): \(err)")
                .foregroundColor(.red)
        case .fileAccess(let path, let op):
            HStack {
                Image(systemName: "filemenu.and.cursorarrow")
                Text("\(op): \(path)")
            }
            .font(.caption)
            .padding(4)
            .background(Color.blue.opacity(0.1))
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
        case .unknown(let type):
            Text("Unknown event: \(type)")
                .font(.caption)
        }
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
