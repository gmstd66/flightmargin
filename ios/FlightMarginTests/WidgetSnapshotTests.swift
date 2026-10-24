import Foundation
import XCTest
@testable import FlightMargin

final class WidgetSnapshotTests: XCTestCase {
    func testSnapshotRoundTripsWithoutSecretFields() throws {
        let snapshot = makeSnapshot()
        let data = try JSONEncoder().encode(snapshot)
        let decoded = try JSONDecoder().decode(WidgetSnapshot.self, from: data)

        XCTAssertEqual(decoded, snapshot)
        let keys = Set(try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any]).keys)
        XCTAssertEqual(keys, [
            "schemaVersion", "generatedAt", "refreshedAt", "hostDisplayName",
            "fiveHourUsed", "fiveHourRemaining", "weeklyUsed", "weeklyRemaining",
            "planType", "availability", "history"
        ])
        for forbidden in ["credential", "token", "deviceID", "deviceUUID", "bearer", "prompt"] {
            XCTAssertFalse(String(decoding: data, as: UTF8.self).localizedCaseInsensitiveContains(forbidden))
        }
    }

    func testHistoryIsBoundedAndSuppressesExactDuplicate() {
        var snapshot = makeSnapshot(history: [])
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        for index in 0..<(WidgetConstants.historyLimit + 10) {
            let history = snapshot.appendingHistory(
                timestamp: start.addingTimeInterval(Double(index)),
                fiveHourUsed: Double(index)
            )
            snapshot = makeSnapshot(history: history)
        }
        XCTAssertEqual(snapshot.history.count, WidgetConstants.historyLimit)
        let duplicate = snapshot.appendingHistory(
            timestamp: snapshot.history.last!.timestamp,
            fiveHourUsed: snapshot.history.last!.fiveHourUsed
        )
        XCTAssertEqual(duplicate, snapshot.history)
    }

    func testFreshStaleAndOfflineCalculation() {
        let now = Date(timeIntervalSince1970: 1_700_000_000)
        XCTAssertEqual(makeSnapshot(refreshedAt: now).freshness(at: now), .fresh)
        XCTAssertEqual(
            makeSnapshot(refreshedAt: now.addingTimeInterval(-WidgetConstants.staleInterval - 1))
                .freshness(at: now),
            .stale
        )
        XCTAssertEqual(makeSnapshot(refreshedAt: now, availability: .offline).freshness(at: now), .offline)
    }

    func testStoreRoundTripUsesInjectableFileURL() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("FlightMarginWidgetTests-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = WidgetSnapshotStore(fileURL: directory.appendingPathComponent("snapshot.json"))
        let snapshot = makeSnapshot()

        try store.write(snapshot)

        XCTAssertEqual(store.read(), snapshot)
        XCTAssertTrue(store.remove())
        XCTAssertNil(store.read())
    }

    func testAppWriterSanitizesQuotaAndOnlyMarksOfflineOnce() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("FlightMarginWidgetWriterTests-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = WidgetSnapshotStore(fileURL: directory.appendingPathComponent("snapshot.json"))
        let writer = AppGroupWidgetSnapshotWriter(store: store)
        let response = try RelayJSON.decoder().decode(QuotaEnvelope.self, from: Data(quotaJSON.utf8))
        let refreshedAt = Date(timeIntervalSince1970: 1_700_000_000)

        XCTAssertTrue(writer.recordSuccessfulRefresh(response, refreshedAt: refreshedAt))
        let snapshot = try XCTUnwrap(store.read())
        XCTAssertEqual(snapshot.hostDisplayName, "COXON")
        XCTAssertEqual(snapshot.fiveHourUsed, 42.5)
        XCTAssertEqual(snapshot.fiveHourRemaining, 57.5)
        XCTAssertEqual(snapshot.history.count, 1)
        XCTAssertEqual(snapshot.availability, .current)

        XCTAssertTrue(writer.markOffline(generatedAt: refreshedAt.addingTimeInterval(1)))
        XCTAssertFalse(writer.markOffline(generatedAt: refreshedAt.addingTimeInterval(2)))
        XCTAssertEqual(store.read()?.availability, .offline)
    }

    private func makeSnapshot(
        refreshedAt: Date = Date(timeIntervalSince1970: 1_700_000_000),
        availability: WidgetSnapshot.Availability = .current,
        history: [WidgetHistorySample] = []
    ) -> WidgetSnapshot {
        WidgetSnapshot(
            schemaVersion: 1, generatedAt: refreshedAt, refreshedAt: refreshedAt,
            hostDisplayName: "COXON", fiveHourUsed: 42.5, fiveHourRemaining: 57.5,
            fiveHourResetAt: nil, weeklyUsed: 21, weeklyRemaining: 79,
            weeklyResetAt: nil, planType: "plus", availability: availability,
            history: history
        )
    }
}
