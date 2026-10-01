import Foundation
import Security

final class KeychainDeviceIdentityStore: DeviceIdentityStoring {
    static let service = "com.gmstd.flightmargin.dev.device-identity"
    private let account: String

    init(account: String = "primary") { self.account = account }

    func load() throws -> DeviceIdentity? {
        var query = baseQuery
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess else { throw SecureStorageError.keychain(status) }
        guard let data = result as? Data,
              let identity = try? JSONDecoder().decode(DeviceIdentity.self, from: data) else {
            throw SecureStorageError.unexpectedData
        }
        return identity
    }

    func save(_ identity: DeviceIdentity) throws {
        let data = try JSONEncoder().encode(identity)
        var query = baseQuery
        query[kSecValueData as String] = data
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        let status = SecItemAdd(query as CFDictionary, nil)
        if status == errSecDuplicateItem {
            let update = [
                kSecValueData as String: data,
                kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
            ] as CFDictionary
            let updated = SecItemUpdate(baseQuery as CFDictionary, update)
            guard updated == errSecSuccess else { throw SecureStorageError.keychain(updated) }
        } else if status != errSecSuccess {
            throw SecureStorageError.keychain(status)
        }
    }

    func delete() throws {
        let status = SecItemDelete(baseQuery as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw SecureStorageError.keychain(status)
        }
    }

    private var baseQuery: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: Self.service,
            kSecAttrAccount as String: account,
            kSecAttrSynchronizable as String: kCFBooleanFalse as Any,
        ]
    }
}
