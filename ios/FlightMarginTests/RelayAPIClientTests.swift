import Foundation
import XCTest
@testable import FlightMargin

final class RelayAPIClientTests: XCTestCase {
    override func tearDown() { MockURLProtocol.handler = nil; super.tearDown() }

    func testTokenClaimUsesExactBodyAndValidatesResponse() async throws {
        let token = "fmp1.33333333-3333-4333-8333-333333333333.UFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFA"
        MockURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/relay-v1/v1/pairings/claim")
            XCTAssertEqual(request.httpMethod, "POST")
            let json = try XCTUnwrap(JSONSerialization.jsonObject(with: requestBodyData(request)) as? [String: Any])
            XCTAssertEqual(Set(json.keys), Set(["pairing_token", "device_id", "display_name", "platform", "credential"]))
            XCTAssertEqual(json["pairing_token"] as? String, token)
            XCTAssertNil(json["manual_code"])
            XCTAssertEqual(json["device_id"] as? String, testIdentity.deviceID.uuidString)
            XCTAssertEqual(json["display_name"] as? String, "iPhone")
            XCTAssertEqual(json["platform"] as? String, "ios")
            XCTAssertEqual(json["credential"] as? String, testIdentity.credential)
            let body = #"{"api_version":1,"paired":true,"device_id":"44444444-4444-4444-8444-444444444444","host_id":"11111111-1111-4111-8111-111111111111"}"#
            return (response(request), Data(body.utf8))
        }
        let client = try RelayAPIClient(session: MockURLProtocol.session())
        let result = try await client.claim(method: .token(token), identity: testIdentity, displayName: "iPhone")
        XCTAssertTrue(result.paired)
    }

    func testManualClaimContainsNoToken() async throws {
        MockURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/relay-v1/v1/pairings/claim")
            XCTAssertEqual(request.httpMethod, "POST")
            let json = try XCTUnwrap(JSONSerialization.jsonObject(with: requestBodyData(request)) as? [String: Any])
            XCTAssertEqual(Set(json.keys), Set(["manual_code", "device_id", "display_name", "platform", "credential"]))
            XCTAssertEqual(json["manual_code"] as? String, "01234-56789")
            XCTAssertNil(json["pairing_token"])
            XCTAssertEqual(json["device_id"] as? String, testIdentity.deviceID.uuidString)
            XCTAssertEqual(json["display_name"] as? String, "iPhone")
            XCTAssertEqual(json["platform"] as? String, "ios")
            XCTAssertEqual(json["credential"] as? String, testIdentity.credential)
            let body = #"{"api_version":1,"paired":true,"device_id":"44444444-4444-4444-8444-444444444444","host_id":"11111111-1111-4111-8111-111111111111"}"#
            return (response(request), Data(body.utf8))
        }
        _ = try await RelayAPIClient(session: MockURLProtocol.session()).claim(
            method: .manualCode("01234-56789"), identity: testIdentity, displayName: "iPhone")
    }

    func testQuotaBearerAndNullableFieldsDecode() async throws {
        MockURLProtocol.handler = { request in
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer \(testIdentity.credential)")
            XCTAssertEqual(request.httpMethod, "GET")
            return (response(request), Data(quotaJSON.utf8))
        }
        let quota = try await RelayAPIClient(session: MockURLProtocol.session()).fetchQuota(credential: testIdentity.credential)
        XCTAssertEqual(quota.quota?.fiveHourUsed, 42.5)
        XCTAssertNil(quota.quota?.weeklyUsed)
        XCTAssertNil(quota.host.appVersion)
    }

    func testAPIVersionCheckedAndErrorsAreSanitized() async throws {
        MockURLProtocol.handler = { request in
            (response(request), Data(#"{"api_version":2,"host":{},"quota":null}"#.utf8))
        }
        do {
            _ = try await RelayAPIClient(session: MockURLProtocol.session()).fetchQuota(credential: testIdentity.credential)
            XCTFail("Expected failure")
        } catch {
            XCTAssertEqual(error as? RelayClientError, .unsupportedAPIVersion)
            XCTAssertFalse(error.localizedDescription.contains(testIdentity.credential))
        }
    }

    func testPairingRejectionAndUnavailableErrorsDoNotExposeSubmittedValues() async throws {
        let submitted = "01234-56789"
        for (status, expected) in [(400, RelayClientError.pairingRejected), (503, .unavailable)] {
            MockURLProtocol.handler = { request in
                (response(request, status: status), Data(#"{"detail":"server detail"}"#.utf8))
            }
            do {
                _ = try await RelayAPIClient(session: MockURLProtocol.session()).claim(
                    method: .manualCode(submitted), identity: testIdentity, displayName: "iPhone")
                XCTFail("Expected status \(status) to fail")
            } catch {
                XCTAssertEqual(error as? RelayClientError, expected)
                XCTAssertFalse(error.localizedDescription.contains(submitted))
                XCTAssertFalse(error.localizedDescription.contains(testIdentity.credential))
            }
        }
    }
}
