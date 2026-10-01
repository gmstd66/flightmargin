import Foundation

protocol DeviceIdentityStoring {
    func load() throws -> DeviceIdentity?
    func save(_ identity: DeviceIdentity) throws
    func delete() throws
}

final class InMemoryDeviceIdentityStore: DeviceIdentityStoring {
    private(set) var identity: DeviceIdentity?

    init(identity: DeviceIdentity? = nil) { self.identity = identity }
    func load() throws -> DeviceIdentity? { identity }
    func save(_ identity: DeviceIdentity) throws { self.identity = identity }
    func delete() throws { identity = nil }
}

extension DeviceIdentityStoring {
    func loadOrCreate() throws -> DeviceIdentity {
        if let identity = try load() { return identity }
        let identity = try DeviceIdentity.generate()
        try save(identity)
        return identity
    }
}
