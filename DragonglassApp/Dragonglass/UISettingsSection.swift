import SwiftUI

struct UISettingsSection: View {
    @EnvironmentObject var client: AgentClient
    @AppStorage("closePopoverOnFocusLoss") private var closePopoverOnFocusLoss = false

    var body: some View {
        VStack(spacing: 8) {
            HStack {
                Text("Detailed tool events")
                Spacer()
                Toggle("", isOn: $client.detailedToolEvents)
                    .toggleStyle(.switch)
                    .controlSize(.small)
                    .labelsHidden()
            }
            HStack {
                Text("Close popover when clicking another window")
                Spacer()
                Toggle("", isOn: $closePopoverOnFocusLoss)
                    .toggleStyle(.switch)
                    .controlSize(.small)
                    .labelsHidden()
            }
        }
        .frame(maxWidth: .infinity)
    }
}
