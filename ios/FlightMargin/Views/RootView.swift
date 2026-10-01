import SwiftUI

struct RootView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        Group {
            switch state.phase {
            case .unpaired, .pairing:
                UnpairedView()
            case .loading:
                NavigationStack {
                    ProgressView("Loading latest quota…")
                        .navigationTitle("FlightMargin")
                }
            case .connected, .offline:
                DashboardView()
            }
        }
        .tint(Color(red: 0.20, green: 0.58, blue: 0.48))
    }
}
