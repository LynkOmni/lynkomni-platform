import XCTest
@testable import LynkCore

final class IdsTests: XCTestCase {
    let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("contract")

    func testVectorsFromThePythonReference() throws {
        let reg = try Registry(json: Data(contentsOf: root.appendingPathComponent("identifier-registry.v1.json")))
        XCTAssertEqual(reg.count, 38)
        let v = try JSONSerialization.jsonObject(with: Data(contentsOf: root.appendingPathComponent("vectors/identifiers.v1.json"))) as! [String: Any]
        for c in v["valid"] as! [[String: Any]] { XCTAssertEqual(try parseId(reg, c["id"] as! String).payload, c["payload"] as? String) }
        for c in v["invalid"] as! [[String: Any]] { XCTAssertThrowsError(try parseId(reg, c["id"] as! String)) }
    }

    func testOfflineWindows() { XCTAssertEqual(maxOfflineDays(role: "owner"), 7); XCTAssertEqual(maxOfflineDays(role: "cashier"), 14) }
}
