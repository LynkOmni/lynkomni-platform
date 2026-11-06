// swift-tools-version:5.9
// NOT built in the sandbox (no Swift toolchain there). CI runs `swift test` on Linux (ci.yml) and weekly on macOS (ios-macos.yml).
import PackageDescription

let package = Package(
    name: "LynkCore",
    products: [.library(name: "LynkCore", targets: ["LynkCore"])],
    targets: [
        .target(name: "LynkCore"),
        .testTarget(name: "LynkCoreTests", dependencies: ["LynkCore"]),
    ]
)
