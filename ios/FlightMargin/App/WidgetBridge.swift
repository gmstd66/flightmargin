import Foundation
import WidgetKit

protocol WidgetSnapshotWriting {
    @discardableResult func recordSuccessfulRefresh(_ response: QuotaEnvelope, refreshedAt: Date) -> Bool
    @discardableResult func markOffline(generatedAt: Date) -> Bool
    @discardableResult func clearSnapshot() -> Bool
}

protocol WidgetTimelineReloading {
    func reloadFlightMarginWidget()
}

final class AppGroupWidgetSnapshotWriter: WidgetSnapshotWriting {
    private let store: WidgetSnapshotStore

    init(store: WidgetSnapshotStore = WidgetSnapshotStore()) {
        self.store = store
    }

    func recordSuccessfulRefresh(_ response: QuotaEnvelope, refreshedAt: Date) -> Bool {
        guard let quota = response.quota else { return false }
        let priorHistory = store.read()?.history ?? []
        let seed = WidgetSnapshot(
            schemaVersion: 1, generatedAt: refreshedAt, refreshedAt: refreshedAt,
            hostDisplayName: nil, fiveHourUsed: nil, fiveHourRemaining: nil,
            fiveHourResetAt: nil, weeklyUsed: nil, weeklyRemaining: nil,
            weeklyResetAt: nil, planType: nil, availability: .current,
            history: priorHistory
        )
        let snapshot = WidgetSnapshot(
            schemaVersion: 1,
            generatedAt: refreshedAt,
            refreshedAt: refreshedAt,
            hostDisplayName: response.host.displayName,
            fiveHourUsed: quota.fiveHourUsed,
            fiveHourRemaining: quota.fiveHourRemaining,
            fiveHourResetAt: quota.fiveHourResetAt,
            weeklyUsed: quota.weeklyUsed,
            weeklyRemaining: quota.weeklyRemaining,
            weeklyResetAt: quota.weeklyResetAt,
            planType: quota.planType,
            availability: .current,
            history: seed.appendingHistory(
                timestamp: quota.sampledAt,
                fiveHourUsed: quota.fiveHourUsed
            )
        )
        do {
            try store.write(snapshot)
            return true
        } catch {
            return false
        }
    }

    func markOffline(generatedAt: Date) -> Bool {
        guard let current = store.read(), current.availability != .offline else { return false }
        do {
            try store.write(current.withAvailability(.offline, generatedAt: generatedAt))
            return true
        } catch {
            return false
        }
    }

    func clearSnapshot() -> Bool {
        store.remove()
    }
}

struct SystemWidgetTimelineReloader: WidgetTimelineReloading {
    func reloadFlightMarginWidget() {
        WidgetCenter.shared.reloadTimelines(ofKind: WidgetConstants.kind)
    }
}
