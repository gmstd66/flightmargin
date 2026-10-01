import SwiftUI

@main
struct FlightMarginApp: App {
    @StateObject private var state = AppState()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(state)
                .onOpenURL { state.handle($0) }
                .task { state.launch() }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active { state.startForegroundRefresh() }
            else { state.stopForegroundRefresh() }
        }
    }
}
