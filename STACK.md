# LynkOmni language and technology allocation

| Language | Responsibility | Where | State here |
|---|---|---|---|
| TypeScript | Web, PWA, dashboards, Node.js services | `ts/` now; production backend and PWA next | compiled and tested (11 tests) |
| SQL | Queries, transactions, integrity, reporting | `sql/` | SQLite tested (6 tests); PostgreSQL written, not run |
| Rust | Offline engine, sync, protocols, performance | `rust/lynk-offline` (JNI, static library, WebAssembly) | written, not compiled |
| Kotlin | Native Android | `android/core` | written, not built |
| Swift | Native iOS | `ios/` | written, not built |
| Python | AI services, ML, automation, data processing, executable reference spec | repository root packages and `tests/` | 144 tests passing |

One Rust offline core, three shells (PWA, Android, iOS). The Python platform is the reference model and test oracle; production services are ported to TypeScript one by one, using `tests/` and `contract/vectors/` as the acceptance suite.
Shared across languages: `contract/identifier-registry.v1.json`, `contract/vectors/*.json`, the event contract in `contract/`.
Supporting technology: PostgreSQL and SQLite; SQLCipher and OS keystores; S3-compatible object storage; containers, Prometheus, age-encrypted backups with restore tests (`infra/`); GitHub Actions CI and a manually approved CD workflow (`.github/workflows/`).
Run what runs here: `python3 -m unittest discover -s tests -t .` and `cd ts && tsc -p . && node --test "dist/test/*.test.js"`. CI runs the rest.

v0.9 additions: `design/` holds the single colour and font source (`tokens.v1.json`), its generator, the font release gate and the accessibility gate (`check_a11y.py`). `services/improvements.py` and `services/sealing.py` hold the approved improvements; sealing uses the `cryptography` library (X25519, HKDF, ChaCha20-Poly1305) and needs a security review. `core/devicedb.py` and `contract/device-storage.v1.json` set the rule that production device databases are SQLCipher-encrypted; no encrypted database has been opened here because SQLCipher is not installed. The Rust crate could not be built here: its dependencies (for example `hex`) cannot be downloaded without network access.
