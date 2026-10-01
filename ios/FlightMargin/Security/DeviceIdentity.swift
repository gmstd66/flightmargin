import Foundation
import Security

struct DeviceIdentity: Codable, Equatable {
    let deviceID: UUID
    let credential: String

    static func generate() throws -> DeviceIdentity {
        var bytes = [UInt8](repeating: 0, count: 32)
        guard SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) == errSecSuccess else {
            throw SecureStorageError.randomGenerationFailed
        }
        let secret = Data(bytes).base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
        return DeviceIdentity(
            deviceID: UUID(),
            credential: "fmd1.\(UUID().uuidString.lowercased()).\(secret)"
        )
    }
}

enum SecureStorageError: Error {
    case randomGenerationFailed
    case encodingFailed
    case unexpectedData
    case keychain(OSStatus)
}
