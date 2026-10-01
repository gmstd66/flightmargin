import Foundation

enum RelayJSON {
    static func decoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { value in
            let container = try value.singleValueContainer()
            let string = try container.decode(String.self)
            for options: ISO8601DateFormatter.Options in [
                [.withInternetDateTime, .withFractionalSeconds],
                [.withInternetDateTime],
            ] {
                let formatter = ISO8601DateFormatter()
                formatter.formatOptions = options
                if let date = formatter.date(from: string) { return date }
            }
            throw DecodingError.dataCorruptedError(
                in: container, debugDescription: "Invalid relay timestamp")
        }
        return decoder
    }
}

struct QuotaEnvelope: Codable, Equatable {
    let apiVersion: Int
    let host: HostSummary
    let quota: QuotaSnapshot?

    enum CodingKeys: String, CodingKey {
        case apiVersion = "api_version"
        case host, quota
    }
}

struct HostSummary: Codable, Equatable {
    let id: UUID
    let displayName: String
    let platform: String
    let appVersion: String?
    let lastSeenAt: Date?

    enum CodingKeys: String, CodingKey {
        case id
        case displayName = "display_name"
        case platform
        case appVersion = "app_version"
        case lastSeenAt = "last_seen_at"
    }
}

struct QuotaSnapshot: Codable, Equatable {
    let schemaVersion: Int
    let sampledAt: Date
    let receivedAt: Date
    let fiveHourUsed: Double?
    let fiveHourResetAt: Date?
    let weeklyUsed: Double?
    let weeklyResetAt: Date?
    let planType: String?
    let resetCreditsAvailable: Int?
    let creditsBalance: Double?
    let spendControlReached: Bool?
    let rateLimitReachedType: String?
    let collectorState: String
    let collectorMessageCode: String?

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case sampledAt = "sampled_at"
        case receivedAt = "received_at"
        case fiveHourUsed = "five_hour_used"
        case fiveHourResetAt = "five_hour_reset_at"
        case weeklyUsed = "weekly_used"
        case weeklyResetAt = "weekly_reset_at"
        case planType = "plan_type"
        case resetCreditsAvailable = "reset_credits_available"
        case creditsBalance = "credits_balance"
        case spendControlReached = "spend_control_reached"
        case rateLimitReachedType = "rate_limit_reached_type"
        case collectorState = "collector_state"
        case collectorMessageCode = "collector_message_code"
    }

    var fiveHourRemaining: Double? { fiveHourUsed.map { max(0, 100 - $0) } }
    var weeklyRemaining: Double? { weeklyUsed.map { max(0, 100 - $0) } }
}
