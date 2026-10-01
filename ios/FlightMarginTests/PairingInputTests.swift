import Foundation
import XCTest
@testable import FlightMargin

final class PairingInputTests: XCTestCase {
    func testManualCodeNormalization() {
        XCTAssertEqual(ManualCode.normalize("01234-56789"), "01234-56789")
        XCTAssertEqual(ManualCode.normalize("abcde fghjk"), "ABCDE-FGHJK")
        XCTAssertEqual(ManualCode.normalize("0123456789"), "01234-56789")
        XCTAssertNil(ManualCode.normalize("ABCDE-IOU12"))
        XCTAssertNil(ManualCode.normalize("SHORT"))
    }

    func testValidPairingLink() throws {
        let token = "fmp1.33333333-3333-4333-8333-333333333333.UFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFA"
        let url = URL(string: "flightmargin://pair/v1?token=\(token)")!
        XCTAssertEqual(try PairingLinkParser.parse(url), token)
    }

    func testInvalidPairingLinks() {
        let values = [
            "https://pair/v1?token=fmp1.bad.bad",
            "flightmargin://wrong/v1?token=fmp1.bad.bad",
            "flightmargin://pair/v2?token=fmp1.bad.bad",
            "flightmargin://pair/v1",
            "flightmargin://pair/v1?token=fmp1.bad.bad",
        ]
        for value in values {
            XCTAssertThrowsError(try PairingLinkParser.parse(URL(string: value)!))
        }
    }
}
