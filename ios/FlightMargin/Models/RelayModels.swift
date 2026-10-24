import Foundation

struct PairingClaimRequest: Encodable, Equatable {
    let pairingToken: String?
    let manualCode: String?
    let deviceID: UUID
    let displayName: String
    let platform: String
    let credential: String

    enum CodingKeys: String, CodingKey {
        case pairingToken = "pairing_token"
        case manualCode = "manual_code"
        case deviceID = "device_id"
        case displayName = "display_name"
        case platform
        case credential
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(pairingToken, forKey: .pairingToken)
        try container.encodeIfPresent(manualCode, forKey: .manualCode)
        try container.encode(deviceID.uuidString.lowercased(), forKey: .deviceID)
        try container.encode(displayName, forKey: .displayName)
        try container.encode(platform, forKey: .platform)
        try container.encode(credential, forKey: .credential)
    }
}

struct PairingClaimResponse: Decodable, Equatable {
    let apiVersion: Int
    let paired: Bool
    let deviceID: UUID
    let hostID: UUID

    enum CodingKeys: String, CodingKey {
        case apiVersion = "api_version"
        case paired
        case deviceID = "device_id"
        case hostID = "host_id"
    }
}

struct RelayErrorResponse: Decodable {
    let detail: String?
}

enum PairingMethod: Equatable {
    case token(String)
    case manualCode(String)
}
