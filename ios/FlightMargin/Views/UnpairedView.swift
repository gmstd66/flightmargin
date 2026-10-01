import SwiftUI

struct UnpairedView: View {
    @EnvironmentObject private var state: AppState
    @State private var showingCode = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()
                Image(systemName: "gauge.with.dots.needle.67percent")
                    .font(.system(size: 62, weight: .light))
                    .foregroundStyle(.tint)
                Text("FlightMargin")
                    .font(.largeTitle.bold())
                Text("See the latest Codex quota from a paired FlightMargin host. No account or login is required.")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)
                if state.phase == .pairing {
                    ProgressView("Pairing this iPhone…")
                } else {
                    Button("Enter pairing code") { showingCode = true }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                }
                Text("You can also open a FlightMargin QR pairing link on this iPhone.")
                    .font(.footnote)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                Spacer()
            }
            .padding()
            .sheet(isPresented: $showingCode) { PairingView() }
            .alert("Pairing problem", isPresented: Binding(
                get: { state.pairingError != nil },
                set: { if !$0 { state.pairingError = nil } }
            )) { Button("OK", role: .cancel) {} } message: {
                Text(state.pairingError ?? "")
            }
        }
    }
}
