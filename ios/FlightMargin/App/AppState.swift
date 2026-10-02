import Combine
import Foundation

@MainActor
final class AppState: ObservableObject {
    enum Phase: Equatable {
        case unpaired
        case pairing
        case loading
        case connected
        case offline(String)
    }

    @Published private(set) var phase: Phase = .unpaired
    @Published private(set) var quota: QuotaEnvelope?
    @Published private(set) var lastSuccessfulRefresh: Date?
    @Published var pairingError: String?

    private let identityStore: DeviceIdentityStoring
    private let api: RelayAPIClientProtocol
    private let defaults: UserDefaults
    private var refreshTask: Task<Void, Never>?
    private var periodicTask: Task<Void, Never>?
    private var isRefreshing = false

    private enum Key {
        static let pairedHostID = "paired_host_id"
        static let cachedQuota = "cached_quota_v1"
        static let lastRefresh = "last_successful_refresh"
    }

    init(identityStore: DeviceIdentityStoring = KeychainDeviceIdentityStore(),
         api: RelayAPIClientProtocol? = nil,
         defaults: UserDefaults = .standard) {
        self.identityStore = identityStore
        self.api = api ?? Self.defaultAPI()
        self.defaults = defaults
        restoreNonSecretState()
    }

    private static func defaultAPI() -> RelayAPIClientProtocol {
        #if DEBUG
        if let value = ProcessInfo.processInfo.environment["FLIGHTMARGIN_RELAY_ENDPOINT"],
           let url = URL(string: value),
           let client = try? RelayAPIClient(endpoint: url, allowInsecureLoopback: true) {
            return client
        }
        #endif
        return try! RelayAPIClient()
    }

    var isPaired: Bool { defaults.string(forKey: Key.pairedHostID) != nil }
    var isStale: Bool {
        if case .offline = phase { return true }
        guard let sample = quota?.quota?.sampledAt else { return false }
        return Date().timeIntervalSince(sample) > 180
    }

    func launch() {
        guard phase != .pairing else { return }
        guard isPaired else { phase = .unpaired; return }
        phase = quota == nil ? .loading : .connected
        startForegroundRefresh()
    }

    func handle(_ url: URL) {
        do {
            let token = try PairingLinkParser.parse(url)
            pair(using: .token(token))
        } catch {
            pairingError = "That FlightMargin pairing link is invalid."
        }
    }

    func pair(manualInput: String, onFailure: ((String) -> Void)? = nil) {
        guard let code = ManualCode.normalize(manualInput) else {
            presentPairingError("Enter a valid 10-character pairing code.", onFailure: onFailure)
            return
        }
        pair(using: .manualCode(code), onFailure: onFailure)
    }

    func pair(using method: PairingMethod, onFailure: ((String) -> Void)? = nil) {
        guard !isPaired, refreshTask == nil else { return }
        pairingError = nil
        phase = .pairing
        refreshTask = Task { [weak self] in
            guard let self else { return }
            defer { refreshTask = nil }
            do {
                // Identity is committed to Keychain before transport starts so a
                // lost success response can be retried with exactly the same values.
                let identity = try identityStore.loadOrCreate()
                let response = try await api.claim(
                    method: method,
                    identity: identity,
                    displayName: "iPhone"
                )
                guard response.apiVersion == 1, response.paired,
                      response.deviceID == identity.deviceID else {
                    throw RelayClientError.invalidResponse
                }
                defaults.set(response.hostID.uuidString.lowercased(), forKey: Key.pairedHostID)
                phase = .loading
                await refresh()
                startForegroundRefresh()
            } catch {
                phase = .unpaired
                presentPairingError(sanitized(error), onFailure: onFailure)
            }
        }
    }

    func refresh() async {
        guard isPaired, !isRefreshing else { return }
        isRefreshing = true
        defer { isRefreshing = false }
        do {
            guard let identity = try identityStore.load() else {
                try clearLocalState()
                return
            }
            let response = try await api.fetchQuota(credential: identity.credential)
            guard response.apiVersion == 1 else { throw RelayClientError.unsupportedAPIVersion }
            quota = response
            lastSuccessfulRefresh = Date()
            cache(response)
            phase = .connected
        } catch {
            phase = .offline(quota == nil
                ? "Unable to refresh quota."
                : "Unable to refresh. Showing the last available quota.")
        }
    }

    func startForegroundRefresh() {
        guard isPaired else { return }
        periodicTask?.cancel()
        periodicTask = Task { [weak self] in
            await self?.refresh()
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(60))
                guard !Task.isCancelled else { return }
                await self?.refresh()
            }
        }
    }

    func stopForegroundRefresh() {
        periodicTask?.cancel()
        periodicTask = nil
    }

    func resetPairing() throws {
        stopForegroundRefresh()
        refreshTask?.cancel()
        refreshTask = nil
        try clearLocalState()
    }

    private func clearLocalState() throws {
        try identityStore.delete()
        defaults.removeObject(forKey: Key.pairedHostID)
        defaults.removeObject(forKey: Key.cachedQuota)
        defaults.removeObject(forKey: Key.lastRefresh)
        quota = nil
        lastSuccessfulRefresh = nil
        pairingError = nil
        phase = .unpaired
    }

    private func restoreNonSecretState() {
        if let data = defaults.data(forKey: Key.cachedQuota) {
            quota = try? RelayJSON.decoder().decode(QuotaEnvelope.self, from: data)
        }
        lastSuccessfulRefresh = defaults.object(forKey: Key.lastRefresh) as? Date
    }

    private func cache(_ response: QuotaEnvelope) {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        if let data = try? encoder.encode(response) {
            defaults.set(data, forKey: Key.cachedQuota)
        }
        defaults.set(lastSuccessfulRefresh, forKey: Key.lastRefresh)
    }

    private func sanitized(_ error: Error) -> String {
        (error as? RelayClientError)?.errorDescription
            ?? "Pairing could not be completed. Check your connection and try again."
    }

    private func presentPairingError(_ message: String, onFailure: ((String) -> Void)?) {
        if let onFailure {
            onFailure(message)
        } else {
            pairingError = message
        }
    }
}
