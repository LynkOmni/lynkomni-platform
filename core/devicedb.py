"""Device database opener. Production devices must use an encrypted database (SQLCipher).
Rule: opening a device database without a key fails unless the caller says explicitly that this is a test or sandbox.
SQLCipher is not installed in the build sandbox, so the encrypted path below is NOT exercised by tests here; Android (SQLCipher for Android), iOS (SQLCipher) and Rust (rusqlite with bundled-sqlcipher) must follow the same rule."""
import sqlite3

class EncryptionUnavailable(RuntimeError): pass

def open_device_db(path, key=None, allow_unencrypted=False):
    if key is None:
        if not allow_unencrypted: raise EncryptionUnavailable("a device database needs an encryption key; only tests may pass allow_unencrypted=True")
        return sqlite3.connect(path)
    try:
        import sqlcipher3 as sc
    except ImportError as e:
        raise EncryptionUnavailable("SQLCipher is not available in this environment") from e
    db = sc.connect(path); db.execute("select quote(?)", (key,)); db.execute(f"pragma key = '{key.replace(chr(39), '')}'")
    db.execute("select count(*) from sqlite_master"); return db   # fails here if the key is wrong
