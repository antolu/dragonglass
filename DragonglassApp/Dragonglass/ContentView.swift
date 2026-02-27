import SwiftUI

struct ContentView: View {
    @EnvironmentObject var backend: BackendManager
    @EnvironmentObject var client: AgentClient
    @State private var inputText = ""
    @State private var showingSettings = false

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
            Text("Dragonglass")
                .font(.headline)
            Spacer()
            Button(action: { showingSettings = true }) {
                Image(systemName: "gear")
            }
            .buttonStyle(.plain)
            .focusable(false)
        }
        .padding()
        .background(Color(NSColor.windowBackgroundColor))
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
                }
                .padding()
            }
            .onChange(of: client.events.count) { _ in
                if let last = client.events.indices.last {
                    proxy.scrollTo(last)
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
        client.sendChat(text: inputText)
        inputText = ""
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
        case .unknown(let type):
            Text("Unknown event: \(type)")
                .font(.caption)
        }
    }
}
