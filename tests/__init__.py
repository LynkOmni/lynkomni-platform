"""Test-only housekeeping: remember every in-memory database a test opens and close them all when the run ends,
so the output stays free of 'unclosed database' ResourceWarnings."""
import atexit
import sqlite3

_real_connect = sqlite3.connect
_opened = []


def _tracked_connect(*args, **kwargs):
    conn = _real_connect(*args, **kwargs)
    _opened.append(conn)
    return conn


def _close_all():
    for conn in _opened:
        try:
            conn.close()
        except Exception:
            pass


sqlite3.connect = _tracked_connect
atexit.register(_close_all)
