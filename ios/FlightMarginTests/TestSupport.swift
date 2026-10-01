import Foundation
import XCTest
@testable import FlightMargin

final class MockURLProtocol: URLProtocol {
    static var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        do {
            guard let handler = Self.handler else { throw URLError(.badServerResponse) }
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }
    override func stopLoading() {}

    static func session() -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [MockURLProtocol.self]
        return URLSession(configuration: configuration)
    }
}

private enum RequestBodyError: Error {
    case missing
    case unreadableStream
}

func requestBodyData(
    _ request: URLRequest,
    file: StaticString = #filePath,
    line: UInt = #line
) throws -> Data {
    if let body = request.httpBody {
        return body
    }

    guard let stream = request.httpBodyStream else {
        XCTFail("Expected the intercepted request to contain an HTTP body", file: file, line: line)
        throw RequestBodyError.missing
    }

    switch stream.streamStatus {
    case .notOpen:
        stream.open()
    case .opening, .open, .reading:
        break
    case .writing, .atEnd, .closed, .error:
        XCTFail("The intercepted request body stream is not readable", file: file, line: line)
        throw RequestBodyError.unreadableStream
    @unknown default:
        XCTFail("The intercepted request body stream has an unsupported state", file: file, line: line)
        throw RequestBodyError.unreadableStream
    }
    defer { stream.close() }

    var body = Data()
    let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: 4_096)
    defer { buffer.deallocate() }

    while true {
        let bytesRead = stream.read(buffer, maxLength: 4_096)
        if bytesRead > 0 {
            body.append(buffer, count: bytesRead)
        } else if bytesRead == 0 {
            return body
        } else {
            XCTFail("Failed to read the intercepted request body stream", file: file, line: line)
            if let streamError = stream.streamError {
                throw streamError
            }
            throw RequestBodyError.unreadableStream
        }
    }
}

func response(_ request: URLRequest, status: Int = 200) -> HTTPURLResponse {
    HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil,
                    headerFields: ["Content-Type": "application/json"])!
}

func assertProductionRelayPath(
    _ request: URLRequest,
    appending route: String,
    file: StaticString = #filePath,
    line: UInt = #line
) {
    let expectedPath = RelayAPIClient.productionEndpoint.appendingPathComponent(route).path
    XCTAssertEqual(request.url?.path, expectedPath, file: file, line: line)
}

let testIdentity = DeviceIdentity(
    deviceID: UUID(uuidString: "44444444-4444-4444-8444-444444444444")!,
    credential: "fmd1.22222222-2222-4222-8222-222222222222.Hx4dHBsaGRgXFhUUExIREA8ODQwLCgkIBwYFBAMCAQA"
)

let quotaJSON = #"{"api_version":1,"host":{"id":"11111111-1111-4111-8111-111111111111","display_name":"COXON","platform":"linux","app_version":null,"last_seen_at":"2026-09-30T12:00:00.123Z"},"quota":{"schema_version":1,"sampled_at":"2026-09-30T12:00:00.123Z","received_at":"2026-09-30T12:00:01.456Z","five_hour_used":42.5,"five_hour_reset_at":null,"weekly_used":null,"weekly_reset_at":null,"plan_type":"plus","reset_credits_available":null,"credits_balance":null,"spend_control_reached":null,"rate_limit_reached_type":null,"collector_state":"ok","collector_message_code":null}}"#

final class FakeRelayAPI: RelayAPIClientProtocol {
    var claimResult: Result<PairingClaimResponse, Error>
    var quotaResult: Result<QuotaEnvelope, Error>
    var claims: [(PairingMethod, DeviceIdentity)] = []
    var fetchCount = 0
    var fetchDelay: Duration = .zero

    init(claimResult: Result<PairingClaimResponse, Error>? = nil,
         quotaResult: Result<QuotaEnvelope, Error>? = nil) {
        self.claimResult = claimResult ?? .success(PairingClaimResponse(
            apiVersion: 1, paired: true, deviceID: testIdentity.deviceID,
            hostID: UUID(uuidString: "11111111-1111-4111-8111-111111111111")!))
        self.quotaResult = quotaResult ?? .success(try! RelayJSON.decoder().decode(QuotaEnvelope.self, from: Data(quotaJSON.utf8)))
    }

    func claim(method: PairingMethod, identity: DeviceIdentity, displayName: String) async throws -> PairingClaimResponse {
        claims.append((method, identity)); return try claimResult.get()
    }
    func fetchQuota(credential: String) async throws -> QuotaEnvelope {
        fetchCount += 1
        if fetchDelay != .zero { try await Task.sleep(for: fetchDelay) }
        return try quotaResult.get()
    }
}

func isolatedDefaults() -> UserDefaults {
    let suite = "FlightMarginTests.\(UUID().uuidString)"
    let defaults = UserDefaults(suiteName: suite)!
    defaults.removePersistentDomain(forName: suite)
    return defaults
}
