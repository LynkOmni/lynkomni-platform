// swift-tools-version:5.9
// NOT built in the sandbox (no Swift toolchain there). Run `swift test` in CI on a macOS runner.
import PackageDescription

let package = Package(
    name: "LynkCore",
    products: [.library(name: "LynkCore", targets: ["LynkCore"])],
    targets: [
        .target(name: "LynkCore"),
        .testTarget(name: "LynkCoreTests", dependencies: ["LynkCore"]),
    ]
)
