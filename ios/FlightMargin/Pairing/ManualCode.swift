import Foundation

enum ManualCode {
    private static let alphabet = CharacterSet(charactersIn: "0123456789ABCDEFGHJKMNPQRSTVWXYZ")

    static func normalize(_ input: String) -> String? {
        let compact = input.uppercased().unicodeScalars.filter {
            $0 != "-" && !CharacterSet.whitespacesAndNewlines.contains($0)
        }
        guard compact.count == 10, compact.allSatisfy({ alphabet.contains($0) }) else { return nil }
        let value = String(compact.map { Character(String($0)) })
        return "\(value.prefix(5))-\(value.suffix(5))"
    }

    static func displayValue(_ input: String) -> String {
        let filtered = input.uppercased().unicodeScalars.filter { alphabet.contains($0) }.prefix(10)
        let value = String(filtered.map { Character(String($0)) })
        guard value.count > 5 else { return value }
        return "\(value.prefix(5))-\(value.dropFirst(5))"
    }
}
