import SwiftUI

struct MicButton: View {
    @EnvironmentObject var sttManager: STTManager
    @EnvironmentObject var client: AgentClient
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
        .onTapGesture {
            if sttManager.isRecording {
                sttManager.stopAndTranscribe()
            } else {
                sttManager.startRecording()
            }
        }
        .disabled(!sttManager.micPermissionGranted || !sttManager.isModelReady || client.isThinking)
        .opacity(sttManager.micPermissionGranted && sttManager.isModelReady ? 1.0 : 0.3)
        .help(
            !sttManager.micPermissionGranted ? "Microphone permission required" :
            !sttManager.isModelReady ? "Download a Whisper model in Settings first" :
            "Hold to dictate"
        )
    }
}
