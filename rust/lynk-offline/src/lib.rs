//! LynkOmni offline engine core. NOT compiled in the build sandbox (no Rust toolchain there): run `cargo test` in CI.
//! The tests read the shared vectors in contract/vectors, produced by the Python reference and verified by the TypeScript package.
pub mod chain;
pub mod ids;
pub mod session;
