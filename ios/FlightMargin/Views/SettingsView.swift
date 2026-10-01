import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var state: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var confirmingReset = false

    var body: some View {
        NavigationStack {
            Form {
                Section("About") {
                    LabeledContent("App", value: "FlightMargin")
                    Text("Accountless companion for a paired FlightMargin host.")
                }
                Section {
                    Button("Reset pairing on this iPhone", role: .destructive) { confirmingReset = true }
                } footer: {
                    Text("This removes the local Keychain identity and cached quota. Relay v1 cannot yet delete or revoke the remote device record.")
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { Button("Done") { dismiss() } }
            .confirmationDialog("Reset pairing?", isPresented: $confirmingReset, titleVisibility: .visible) {
                Button("Reset pairing on this iPhone", role: .destructive) {
                    try? state.resetPairing()
                    dismiss()
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("You will need a new pairing code. This does not revoke the existing remote device record.")
            }
        }
    }
}
