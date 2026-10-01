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
