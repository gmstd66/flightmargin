import Foundation

protocol RelayAPIClientProtocol {
    func claim(method: PairingMethod, identity: DeviceIdentity, displayName: String) async throws -> PairingClaimResponse
    func fetchQuota(credential: String) async throws -> QuotaEnvelope
}

enum RelayClientError: LocalizedError, Equatable {
    case invalidResponse
    case unsupportedAPIVersion
    case pairingRejected
    case unauthorized
    case rateLimited
    case unavailable

    var errorDescription: String? {
        switch self {
        case .pairingRejected: "Pairing code is invalid, expired, or already used."
        case .unauthorized: "This iPhone is no longer authorized."
        case .rateLimited: "Too many attempts. Please wait and try again."
        case .unavailable: "FlightMargin Relay is unavailable. Try again shortly."
        case .unsupportedAPIVersion, .invalidResponse: "The relay returned an unsupported response."
        }
    }
}

final class RejectRedirectDelegate: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest,
                    completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

final class RelayAPIClient: RelayAPIClientProtocol {
    static let productionEndpoint = URL(string: "https://samcdyrwfwrlxzypzgmj.supabase.co/functions/v1/relay-v1")!
    private let endpoint: URL
    private let session: URLSession
    private let encoder = JSONEncoder()
    private let decoder: JSONDecoder

    init(endpoint: URL = productionEndpoint, session: URLSession? = nil,
         allowInsecureLoopback: Bool = false) throws {
        self.endpoint = try EndpointPolicy.validate(endpoint, allowInsecureLoopback: allowInsecureLoopback)
        if let session {
            self.session = session
        } else {
            let configuration = URLSessionConfiguration.ephemeral
            configuration.timeoutIntervalForRequest = 10
            configuration.timeoutIntervalForResource = 15
            configuration.httpShouldSetCookies = false
            self.session = URLSession(configuration: configuration, delegate: RejectRedirectDelegate(), delegateQueue: nil)
        }
        decoder = RelayJSON.decoder()
    }

    func claim(method: PairingMethod, identity: DeviceIdentity, displayName: String) async throws -> PairingClaimResponse {
        let requestBody = PairingClaimRequest(
            pairingToken: method.token, manualCode: method.manualCode,
            deviceID: identity.deviceID, displayName: String(displayName.prefix(120)),
            platform: "ios", credential: identity.credential
        )
        var request = URLRequest(url: endpoint.appendingPathComponent("v1/pairings/claim"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(requestBody)
        let (data, response) = try await perform(request)
        guard response.statusCode == 200 else { throw mapStatus(response.statusCode) }
        guard let result = try? decoder.decode(PairingClaimResponse.self, from: data),
              result.apiVersion == 1 else { throw RelayClientError.unsupportedAPIVersion }
        return result
    }

    func fetchQuota(credential: String) async throws -> QuotaEnvelope {
        var request = URLRequest(url: endpoint.appendingPathComponent("v1/quota"))
        request.httpMethod = "GET"
        request.setValue("Bearer \(credential)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await perform(request)
        guard response.statusCode == 200 else { throw mapStatus(response.statusCode) }
        guard let result = try? decoder.decode(QuotaEnvelope.self, from: data),
              result.apiVersion == 1,
              result.quota == nil || result.quota?.schemaVersion == 1 else {
            throw RelayClientError.unsupportedAPIVersion
        }
        return result
    }

    private func perform(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse, !(300...399).contains(http.statusCode) else {
                throw RelayClientError.invalidResponse
            }
            return (data, http)
        } catch let error as RelayClientError { throw error }
        catch { throw RelayClientError.unavailable }
    }

    private func mapStatus(_ status: Int) -> RelayClientError {
        switch status {
        case 400, 422: .pairingRejected
        case 401, 403: .unauthorized
        case 429: .rateLimited
        case 500...599: .unavailable
        default: .invalidResponse
        }
    }
}

private extension PairingMethod {
    var token: String? { if case let .token(value) = self { value } else { nil } }
    var manualCode: String? { if case let .manualCode(value) = self { value } else { nil } }
}
