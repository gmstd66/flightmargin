import Foundation
import XCTest
@testable import FlightMargin

@MainActor
final class AppStateTests: XCTestCase {
    func testManualClaimFailureUsesLocalPresentationWithoutPublishingSharedError() async throws {
        let api = FakeRelayAPI(claimResult: .failure(RelayClientError.unavailable))
        let state = AppState(
            identityStore: InMemoryDeviceIdentityStore(identity: testIdentity),
            api: api,
            defaults: isolatedDefaults()
        )
        var presentedError: String?

        state.pair(manualInput: "01234-56789") { presentedError = $0 }
        try await Task.sleep(for: .milliseconds(100))

        XCTAssertEqual(presentedError, "FlightMargin Relay is unavailable. Try again shortly.")
        XCTAssertNil(state.pairingError)
        XCTAssertEqual(state.phase, .unpaired)
    }

    func testTokenClaimFailureStillPublishesSharedError() async throws {
        let api = FakeRelayAPI(claimResult: .failure(RelayClientError.pairingRejected))
        let state = AppState(
            identityStore: InMemoryDeviceIdentityStore(identity: testIdentity),
            api: api,
            defaults: isolatedDefaults()
        )

        state.pair(using: .token("unused-by-fake-api"))
        try await Task.sleep(for: .milliseconds(100))

        XCTAssertEqual(state.pairingError, "Pairing code is invalid, expired, or already used.")
        XCTAssertEqual(state.phase, .unpaired)
    }

    func testFailedClaimKeepsStableIdentityAndDoesNotPersistSecret() async throws {
        let store = InMemoryDeviceIdentityStore()
        let api = FakeRelayAPI(claimResult: .failure(RelayClientError.unavailable))
        let defaults = isolatedDefaults()
        let state = AppState(identityStore: store, api: api, defaults: defaults)
        state.pair(using: .manualCode("01234-56789"))
        try await Task.sleep(for: .milliseconds(100))
        let first = try XCTUnwrap(store.identity)
        state.pair(using: .manualCode("01234-56789"))
        try await Task.sleep(for: .milliseconds(100))
        XCTAssertEqual(store.identity, first)
        XCTAssertEqual(api.claims.map { $0.1 }, [first, first])
        XCTAssertFalse(defaults.dictionaryRepresentation().description.contains(first.credential))
    }

    func testSuccessfulClaimPairsFetchesAndDoesNotPersistToken() async throws {
        let store = InMemoryDeviceIdentityStore(identity: testIdentity)
        let api = FakeRelayAPI()
        let defaults = isolatedDefaults()
        let state = AppState(identityStore: store, api: api, defaults: defaults)
        let token = "fmp1.33333333-3333-4333-8333-333333333333.UFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFA"
        state.pair(using: .token(token))
        try await Task.sleep(for: .milliseconds(150))
        XCTAssertTrue(state.isPaired)
        XCTAssertEqual(state.phase, .connected)
        XCTAssertEqual(state.quota?.host.displayName, "COXON")
        XCTAssertFalse(defaults.dictionaryRepresentation().description.contains(token))
        state.stopForegroundRefresh()
    }

    func testOfflineRefreshPreservesPairingAndCachedQuota() async throws {
        let defaults = isolatedDefaults()
        let goodAPI = FakeRelayAPI()
        let state = AppState(identityStore: InMemoryDeviceIdentityStore(identity: testIdentity), api: goodAPI, defaults: defaults)
        state.pair(using: .manualCode("01234-56789"))
        try await Task.sleep(for: .milliseconds(150))
        let cached = state.quota
        goodAPI.quotaResult = .failure(RelayClientError.unavailable)
        await state.refresh()
        XCTAssertTrue(state.isPaired)
        XCTAssertEqual(state.quota, cached)
        if case .offline = state.phase {} else { XCTFail("Expected offline state") }
        state.stopForegroundRefresh()
    }

    func testConcurrentRefreshIsSerialized() async throws {
        let defaults = isolatedDefaults()
        defaults.set(UUID().uuidString, forKey: "paired_host_id")
        let api = FakeRelayAPI(); api.fetchDelay = .milliseconds(100)
        let state = AppState(identityStore: InMemoryDeviceIdentityStore(identity: testIdentity), api: api, defaults: defaults)
        async let first: Void = state.refresh()
        async let second: Void = state.refresh()
        _ = await (first, second)
        XCTAssertEqual(api.fetchCount, 1)
    }

    func testResetRemovesIdentityMetadataQuotaAndReturnsUnpaired() async throws {
        let defaults = isolatedDefaults()
        let store = InMemoryDeviceIdentityStore(identity: testIdentity)
        let state = AppState(identityStore: store, api: FakeRelayAPI(), defaults: defaults)
        state.pair(using: .manualCode("01234-56789"))
        try await Task.sleep(for: .milliseconds(150))
        try state.resetPairing()
        XCTAssertNil(store.identity)
        XCTAssertFalse(state.isPaired)
        XCTAssertNil(state.quota)
        XCTAssertEqual(state.phase, .unpaired)
        XCTAssertNil(defaults.object(forKey: "paired_host_id"))
        XCTAssertNil(defaults.object(forKey: "cached_quota_v1"))
    }
}
