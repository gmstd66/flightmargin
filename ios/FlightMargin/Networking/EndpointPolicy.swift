import Foundation

enum EndpointPolicyError: Error { case invalidEndpoint }

enum EndpointPolicy {
    static func validate(_ url: URL, allowInsecureLoopback: Bool) throws -> URL {
        guard url.user == nil, url.password == nil, url.query == nil, url.fragment == nil else {
            throw EndpointPolicyError.invalidEndpoint
        }
        if url.scheme?.lowercased() == "https" { return url }
        guard allowInsecureLoopback, url.scheme?.lowercased() == "http", let host = url.host,
              isSyntacticLoopback(host) else { throw EndpointPolicyError.invalidEndpoint }
        return url
    }

    static func isSyntacticLoopback(_ host: String) -> Bool {
        if host.lowercased() == "localhost" || host == "::1" { return true }
        let pieces = host.split(separator: ".", omittingEmptySubsequences: false)
        guard pieces.count == 4, pieces.allSatisfy({ UInt8($0) != nil }) else { return false }
        return pieces[0] == "127"
    }
}
