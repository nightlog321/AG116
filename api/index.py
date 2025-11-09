# api/index.py — wrapper to surface import-time errors
import sys, traceback
print("HELLO_WRAPPER", flush=True)

try:
    # your current server.py seems to be at repo root, so import server
    from server import app
    print("✅ Imported server.app", flush=True)
except Exception:
    print("❌ Import-time exception while importing server.app:", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)
    raise
