import Foundation
import XCTest
@testable import FlightMargin

final class EndpointPolicyTests: XCTestCase {
    func testProductionHTTPSAccepted() throws {
        XCTAssertNoThrow(try EndpointPolicy.validate(RelayAPIClient.productionEndpoint, allowInsecureLoopback: false))
    }

    func testOnlySyntacticLoopbackHTTPAcceptedWhenExplicitlyEnabled() {
        for value in ["http://localhost:18093", "http://127.0.0.1:18093", "http://127.99.1.2", "http://[::1]:18093"] {
            XCTAssertNoThrow(try EndpointPolicy.validate(URL(string: value)!, allowInsecureLoopback: true), value)
        }
        for value in ["http://example.com", "http://localhost.example.com", "http://128.0.0.1", "http://2130706433"] {
            XCTAssertThrowsError(try EndpointPolicy.validate(URL(string: value)!, allowInsecureLoopback: true), value)
        }
        XCTAssertThrowsError(try EndpointPolicy.validate(URL(string: "http://localhost:18093")!, allowInsecureLoopback: false))
    }

    func testRedirectDelegateRejectsRedirect() {
        let delegate = RejectRedirectDelegate()
        let expectation = expectation(description: "redirect rejected")
        let original = URLRequest(url: URL(string: "https://example.com")!)
        let task = URLSession.shared.dataTask(with: original)
        delegate.urlSession(URLSession.shared, task: task,
            willPerformHTTPRedirection: HTTPURLResponse(url: original.url!, statusCode: 302, httpVersion: nil, headerFields: nil)!,
            newRequest: URLRequest(url: URL(string: "https://other.example")!)) { request in
                XCTAssertNil(request); expectation.fulfill()
            }
        wait(for: [expectation], timeout: 1)
    }
}
