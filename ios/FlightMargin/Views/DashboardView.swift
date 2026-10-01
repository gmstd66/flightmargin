import SwiftUI

struct DashboardView: View {
    @EnvironmentObject private var state: AppState
    @State private var showingSettings = false

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(spacing: 16) {
                    if case let .offline(message) = state.phase {
                        Label(message, systemImage: "wifi.slash")
                            .font(.footnote).foregroundStyle(.orange)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding().background(.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 12))
                    }
                    if let host = state.quota?.host {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(host.displayName).font(.title2.bold())
                            Text("Plan: \(state.quota?.quota?.planType ?? "Not supplied")")
                                .foregroundStyle(.secondary)
                        }.frame(maxWidth: .infinity, alignment: .leading)
                    }
                    if let quota = state.quota?.quota {
                        QuotaGauge(title: "5-hour", used: quota.fiveHourUsed,
                                   remaining: quota.fiveHourRemaining, reset: quota.fiveHourResetAt)
                        QuotaGauge(title: "Weekly", used: quota.weeklyUsed,
                                   remaining: quota.weeklyRemaining, reset: quota.weeklyResetAt)
                        if quota.resetCreditsAvailable != nil || quota.creditsBalance != nil {
                            HStack {
                                Metric(title: "Reset credits", value: quota.resetCreditsAvailable.map(String.init) ?? "—")
                                Metric(title: "Credit balance", value: quota.creditsBalance.map { $0.formatted() } ?? "—")
                            }
                        }
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Sample: \(quota.sampledAt.formatted(date: .abbreviated, time: .shortened))", systemImage: "clock")
                            if let refreshed = state.lastSuccessfulRefresh {
                                Label("App refresh: \(refreshed.formatted(date: .omitted, time: .standard))", systemImage: "arrow.clockwise")
                            }
                            if state.isStale { Label("Stale data", systemImage: "exclamationmark.triangle").foregroundStyle(.orange) }
                        }.font(.footnote).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading)
                    } else {
                        ContentUnavailableView("Waiting for quota", systemImage: "hourglass",
                            description: Text("The paired host has not supplied a quota sample yet."))
                    }
                }.padding()
            }
            .refreshable { await state.refresh() }
            .navigationTitle("FlightMargin")
            .toolbar { Button { showingSettings = true } label: { Image(systemName: "gearshape") } }
            .sheet(isPresented: $showingSettings) { SettingsView() }
        }
    }
}

private struct QuotaGauge: View {
    let title: String
    let used: Double?
    let remaining: Double?
    let reset: Date?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let used {
                HStack { Text(title).font(.headline); Spacer(); Text("\(used.formatted(.number.precision(.fractionLength(0...1))))% used") }
                ProgressView(value: used, total: 100).tint(.accentColor)
                HStack {
                    Text(remaining.map { "\($0.formatted(.number.precision(.fractionLength(0...1))))% remaining" } ?? "Remaining not supplied")
                    Spacer()
                    Text(reset.map { "Resets \($0.formatted(date: .abbreviated, time: .shortened))" } ?? "Reset not supplied")
                }.font(.caption).foregroundStyle(.secondary)
            } else {
                HStack { Text(title).font(.headline); Spacer(); Text("Usage not supplied").foregroundStyle(.secondary) }
                Text(reset.map { "Resets \($0.formatted(date: .abbreviated, time: .shortened))" } ?? "Reset not supplied")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }.padding().background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
    }
}

private struct Metric: View {
    let title: String
    let value: String
    var body: some View {
        VStack(alignment: .leading) { Text(title).font(.caption).foregroundStyle(.secondary); Text(value).font(.title2.bold()) }
            .frame(maxWidth: .infinity, alignment: .leading).padding().background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
    }
}
