# api/index.py
import sys, traceback

print("🚀 Starting Vercel function import...", flush=True)

try:
    # Import your FastAPI app from your backend package
    from AG116.backend.server import app
    print("✅ FastAPI app imported successfully", flush=True)

except Exception:
    print("❌ Import-time exception while loading AG116.backend.server:", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)
    raise
