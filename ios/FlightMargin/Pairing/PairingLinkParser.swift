import Foundation

enum PairingLinkError: Error { case invalidURL }

enum PairingLinkParser {
    private static let tokenPattern = #"^fmp1\.[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\.[A-Za-z0-9_-]{43}$"#

    static func parse(_ url: URL) throws -> String {
        guard url.scheme?.lowercased() == "flightmargin",
              url.host?.lowercased() == "pair",
              url.path == "/v1",
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              components.queryItems?.filter({ $0.name == "token" }).count == 1,
              let token = components.queryItems?.first(where: { $0.name == "token" })?.value,
              token.range(of: tokenPattern, options: .regularExpression) != nil else {
            throw PairingLinkError.invalidURL
        }
        return token
    }
}
