import Foundation

enum WidgetConstants {
    static let appGroupIdentifier = "group.io.github.gmstd66.flightmargin"
    static let kind = "FlightMarginWidget"
    static let snapshotFilename = "widget-snapshot.json"
    static let historyLimit = 72
    static let staleInterval: TimeInterval = 15 * 60
}

struct WidgetHistorySample: Codable, Equatable {
    let timestamp: Date
    let fiveHourUsed: Double
}

struct WidgetSnapshot: Codable, Equatable {
    enum Availability: String, Codable {
        case current
        case offline
    }

    enum Freshness: Equatable {
        case fresh
        case stale
        case offline
    }

    let schemaVersion: Int
    let generatedAt: Date
    let refreshedAt: Date
    let hostDisplayName: String?
    let fiveHourUsed: Double?
    let fiveHourRemaining: Double?
    let fiveHourResetAt: Date?
    let weeklyUsed: Double?
    let weeklyRemaining: Double?
    let weeklyResetAt: Date?
    let planType: String?
    let availability: Availability
    let history: [WidgetHistorySample]

    func freshness(at date: Date = Date()) -> Freshness {
        if availability == .offline { return .offline }
        return date.timeIntervalSince(refreshedAt) > WidgetConstants.staleInterval
            ? .stale : .fresh
    }

    func appendingHistory(timestamp: Date, fiveHourUsed: Double?) -> [WidgetHistorySample] {
        guard let fiveHourUsed else { return history }
        let sample = WidgetHistorySample(timestamp: timestamp, fiveHourUsed: fiveHourUsed)
        if let last = history.last,
           last.fiveHourUsed == sample.fiveHourUsed,
           abs(last.timestamp.timeIntervalSince(sample.timestamp)) < 1 {
            return history
        }
        return Array((history + [sample]).suffix(WidgetConstants.historyLimit))
    }

    func withAvailability(_ availability: Availability, generatedAt: Date) -> WidgetSnapshot {
        WidgetSnapshot(
            schemaVersion: schemaVersion,
            generatedAt: generatedAt,
            refreshedAt: refreshedAt,
            hostDisplayName: hostDisplayName,
            fiveHourUsed: fiveHourUsed,
            fiveHourRemaining: fiveHourRemaining,
            fiveHourResetAt: fiveHourResetAt,
            weeklyUsed: weeklyUsed,
            weeklyRemaining: weeklyRemaining,
            weeklyResetAt: weeklyResetAt,
            planType: planType,
            availability: availability,
            history: history
        )
    }
}

final class WidgetSnapshotStore {
    enum StoreError: Error { case containerUnavailable }

    private let fileURL: URL?

    init(fileURL: URL?) {
        self.fileURL = fileURL
    }

    convenience init(appGroupIdentifier: String = WidgetConstants.appGroupIdentifier) {
        let container = FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: appGroupIdentifier
        )
        self.init(fileURL: container?.appendingPathComponent(WidgetConstants.snapshotFilename))
    }

    func read() -> WidgetSnapshot? {
        guard let fileURL, let data = try? Data(contentsOf: fileURL) else { return nil }
        return try? Self.decoder().decode(WidgetSnapshot.self, from: data)
    }

    func write(_ snapshot: WidgetSnapshot) throws {
        guard let fileURL else { throw StoreError.containerUnavailable }
        let data = try Self.encoder().encode(snapshot)
        try data.write(to: fileURL, options: .atomic)
    }

    @discardableResult
    func remove() -> Bool {
        guard let fileURL, FileManager.default.fileExists(atPath: fileURL.path) else { return false }
        do {
            try FileManager.default.removeItem(at: fileURL)
            return true
        } catch {
            return false
        }
    }

    private static func encoder() -> JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }

    private static func decoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}
