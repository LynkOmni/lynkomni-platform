import Foundation

/// Input and display validation for LynkOmni identifiers on iOS. The authoritative engine is the Rust core (static library).
public struct Registry {
    private let codes: Set<String>
    public init(json: Data) throws {
        let obj = try JSONSerialization.jsonObject(with: json) as? [String: Any]
        let types = obj?["types"] as? [[String: Any]] ?? []
        codes = Set(types.compactMap { $0["code"] as? String })
    }
    public func has(_ code: String) -> Bool { codes.contains(code) }
    public var count: Int { codes.count }
}

public enum IdError: Error { case notAnIdentifier, unregisteredType, badCheckDigit }

public func luhnDigit(_ p11: String) -> Character {
    var s = 0
    for (i, ch) in p11.reversed().enumerated() { var d = ch.wholeNumberValue! * (i % 2 == 0 ? 2 : 1); if d > 9 { d -= 9 }; s += d }
    return Character(String((10 - s % 10) % 10))
}

public func luhnOk(_ p12: String) -> Bool {
    var s = 0
    for (i, ch) in p12.reversed().enumerated() { guard let n = ch.wholeNumberValue else { return false }; var d = n * (i % 2 == 1 ? 2 : 1); if d > 9 { d -= 9 }; s += d }
    return s % 10 == 0
}

/// Format check only: a well-formed identifier proves nothing about existence or access.
public func parseId(_ reg: Registry, _ id: String) throws -> (code: String, payload: String) {
    let re = try NSRegularExpression(pattern: "^LO([A-Z]{2,4})-(\\d{4})-(\\d{4})-(\\d{4})$")
    let range = NSRange(id.startIndex..., in: id)
    guard let m = re.firstMatch(in: id, range: range) else { throw IdError.notAnIdentifier }
    func g(_ i: Int) -> String { String(id[Range(m.range(at: i), in: id)!]) }
    guard reg.has(g(1)) else { throw IdError.unregisteredType }
    let payload = g(2) + g(3) + g(4)
    guard luhnOk(payload) else { throw IdError.badCheckDigit }
    return (g(1), payload)
}

public func maxOfflineDays(role: String) -> Int { (role == "owner" || role == "manager") ? 7 : 14 }
