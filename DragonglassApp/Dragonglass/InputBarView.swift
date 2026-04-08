import SwiftUI

struct InputBarView: View {
    @EnvironmentObject var client: AgentClient
    @EnvironmentObject var sttManager: STTManager
    @EnvironmentObject var backend: BackendManager
    @Binding var inputText: String
    let onSend: () -> Void
    let onSTT: (String) -> Void

    var body: some View {
        HStack {
            TextField(sttPendingPrompt, text: $inputText)
                .textFieldStyle(.plain)
                .onSubmit(onSend)
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
                Button(action: onSend) {
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
            onSTT(toSend)
        }
    }

    private var sttPendingPrompt: String {
        if sttManager.isRecording { return "Recording…" }
        if sttManager.isTranscribing { return "Transcribing…" }
        if sttManager.pendingText != nil { return "Press Esc to cancel" }
        return "Ask anything..."
    }
}
