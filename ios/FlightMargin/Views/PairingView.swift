import SwiftUI

struct PairingView: View {
    @EnvironmentObject private var state: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var code = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("XXXXX-XXXXX", text: $code)
                        .keyboardType(.asciiCapable)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                        .font(.system(.title3, design: .monospaced))
                        .onChange(of: code) { _, value in code = ManualCode.displayValue(value) }
                } header: { Text("Pairing code") }
                footer: { Text("Enter the code shown by FlightMargin on your computer.") }

                Button {
                    state.pair(manualInput: code)
                } label: {
                    HStack {
                        Spacer()
                        if state.phase == .pairing { ProgressView() }
                        else { Text("Pair iPhone") }
                        Spacer()
                    }
                }
                .disabled(ManualCode.normalize(code) == nil || state.phase == .pairing)
            }
            .navigationTitle("Pair FlightMargin")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } } }
            .onChange(of: state.phase) { _, phase in
                if phase == .connected || phase == .loading { dismiss() }
            }
            .alert("Pairing problem", isPresented: Binding(
                get: { state.pairingError != nil },
                set: { if !$0 { state.pairingError = nil } }
            )) { Button("OK", role: .cancel) {} } message: {
                Text(state.pairingError ?? "")
            }
        }
    }
}
