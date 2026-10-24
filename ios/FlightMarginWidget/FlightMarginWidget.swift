import SwiftUI
import WidgetKit

struct FlightMarginEntry: TimelineEntry {
    let date: Date
    let snapshot: WidgetSnapshot?
}

struct FlightMarginProvider: TimelineProvider {
    private let store = WidgetSnapshotStore()

    func placeholder(in context: Context) -> FlightMarginEntry {
        FlightMarginEntry(date: Date(), snapshot: nil)
    }

    func getSnapshot(in context: Context, completion: @escaping (FlightMarginEntry) -> Void) {
        completion(FlightMarginEntry(date: Date(), snapshot: store.read()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<FlightMarginEntry>) -> Void) {
        let now = Date()
        let entry = FlightMarginEntry(date: now, snapshot: store.read())
        completion(Timeline(entries: [entry], policy: .after(now.addingTimeInterval(15 * 60))))
    }
}

struct FlightMarginWidgetView: View {
    let entry: FlightMarginEntry

    var body: some View {
        Group {
            if let snapshot = entry.snapshot {
                content(snapshot)
            } else {
                emptyState
            }
        }
        .containerBackground(Color(red: 0.035, green: 0.055, blue: 0.07), for: .widget)
        .widgetURL(URL(string: "flightmargin://open"))
    }

    private func content(_ snapshot: WidgetSnapshot) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack {
                Text("FLIGHTMARGIN")
                    .font(.caption2.weight(.semibold))
                    .tracking(1.1)
                    .foregroundStyle(.white.opacity(0.72))
                Spacer()
                freshness(snapshot)
            }
            HStack(alignment: .top, spacing: 28) {
                quotaColumn(title: "5-HOUR", used: snapshot.fiveHourUsed,
                            remaining: snapshot.fiveHourRemaining,
                            resetAt: snapshot.fiveHourResetAt)
                quotaColumn(title: "WEEKLY", used: snapshot.weeklyUsed,
                            remaining: snapshot.weeklyRemaining,
                            resetAt: snapshot.weeklyResetAt)
            }
            UtilizationGraph(samples: snapshot.history)
                .frame(height: 30)
            Text("Updated \(snapshot.refreshedAt, style: .relative)")
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.55))
        }
        .padding(14)
    }

    private var emptyState: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("FLIGHTMARGIN")
                .font(.caption2.weight(.semibold))
                .tracking(1.1)
                .foregroundStyle(.white.opacity(0.72))
            Spacer()
            Text("Open FlightMargin to load quota")
                .font(.headline)
                .foregroundStyle(.white)
            Text("Quota history stays on this iPhone.")
                .font(.caption)
                .foregroundStyle(.white.opacity(0.55))
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
    }

    private func quotaColumn(title: String, used: Double?, remaining: Double?, resetAt: Date?) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(title).font(.caption2.weight(.medium)).foregroundStyle(.white.opacity(0.5))
            Text(percent(used)).font(.system(size: 25, weight: .semibold, design: .rounded))
                .foregroundStyle(utilizationColor(used))
            Text(remaining.map { "\(Int($0.rounded()))% left" } ?? "Unavailable")
                .font(.caption2).foregroundStyle(.white.opacity(0.68))
            if let resetAt {
                Text("Resets \(resetAt, style: .relative)")
                    .font(.system(size: 9)).foregroundStyle(.white.opacity(0.45)).lineLimit(1)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func freshness(_ snapshot: WidgetSnapshot) -> some View {
        let freshness = snapshot.freshness(at: entry.date)
        let text = freshness == .fresh ? "CURRENT" : freshness == .stale ? "STALE" : "OFFLINE · CACHED"
        let color: Color = freshness == .fresh ? .green : freshness == .stale ? .orange : .red
        return Text(text).font(.system(size: 9, weight: .bold)).foregroundStyle(color)
    }

    private func percent(_ value: Double?) -> String {
        value.map { "\(Int($0.rounded()))%" } ?? "—"
    }

    private func utilizationColor(_ value: Double?) -> Color {
        guard let value else { return .white.opacity(0.55) }
        if value >= 90 { return .red }
        if value >= 70 { return .orange }
        return Color(red: 0.35, green: 0.82, blue: 0.78)
    }
}

struct UtilizationGraph: View {
    let samples: [WidgetHistorySample]

    var body: some View {
        Canvas { context, size in
            guard samples.count > 1 else {
                var baseline = Path()
                baseline.move(to: CGPoint(x: 0, y: size.height / 2))
                baseline.addLine(to: CGPoint(x: size.width, y: size.height / 2))
                context.stroke(baseline, with: .color(.white.opacity(0.16)), lineWidth: 1)
                return
            }
            let values = samples.map { min(100, max(0, $0.fiveHourUsed)) }
            var path = Path()
            for (index, value) in values.enumerated() {
                let x = size.width * CGFloat(index) / CGFloat(values.count - 1)
                let y = size.height * (1 - CGFloat(value / 100))
                if index == 0 { path.move(to: CGPoint(x: x, y: y)) }
                else { path.addLine(to: CGPoint(x: x, y: y)) }
            }
            context.stroke(path, with: .color(Color(red: 0.35, green: 0.82, blue: 0.78)),
                           style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
        }
        .accessibilityLabel("Five-hour utilization history")
    }
}

@main
struct FlightMarginWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: WidgetConstants.kind, provider: FlightMarginProvider()) { entry in
            FlightMarginWidgetView(entry: entry)
        }
        .configurationDisplayName("Quota Status")
        .description("Current FlightMargin quota and recent on-device utilization history.")
        .supportedFamilies([.systemMedium])
    }
}
