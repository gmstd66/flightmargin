import Foundation
import XCTest
@testable import FlightMargin

final class DeviceIdentityTests: XCTestCase {
    func testGeneratedIdentityHasValidUUIDAndCanonicalCredential() throws {
        let identity = try DeviceIdentity.generate()
        XCTAssertNotNil(UUID(uuidString: identity.deviceID.uuidString))
        let components = identity.credential.split(separator: ".")
        XCTAssertEqual(components.count, 3)
        XCTAssertEqual(components[0], "fmd1")
        XCTAssertNotNil(UUID(uuidString: String(components[1])))
        XCTAssertEqual(components[2].count, 43)
        XCTAssertFalse(components[2].contains("="))
        let base64 = String(components[2]).replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/") + "="
        XCTAssertEqual(Data(base64Encoded: base64)?.count, 32)
    }

    func testInMemoryStoreSaveLoadDeleteAndStableLoadOrCreate() throws {
        let store = InMemoryDeviceIdentityStore()
        let first = try store.loadOrCreate()
        XCTAssertEqual(try store.loadOrCreate(), first)
        XCTAssertEqual(try store.load(), first)
        try store.delete()
        XCTAssertNil(try store.load())
    }

    func testNativeKeychainRoundTrip() throws {
        let store = KeychainDeviceIdentityStore(account: "test-\(UUID().uuidString)")
        defer { try? store.delete() }
        try store.save(testIdentity)
        XCTAssertEqual(try store.load(), testIdentity)
        try store.delete()
        XCTAssertNil(try store.load())
    }
}
