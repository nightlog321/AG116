# api/index.py — aggressive debug wrapper
import os
import sys
import traceback
import pathlib
from importlib import import_module

def safe_print(*args, **kwargs):
    print(*args, **kwargs, flush=True)

safe_print("=== wrapper import start ===")
safe_print("cwd:", os.getcwd())
safe_print("python:", sys.version)
safe_print("sys.path:")
for p in sys.path:
    safe_print("  ", p)

# list repo top-level and AG116/backend contents (if present)
def list_dir(path):
    try:
        p = pathlib.Path(path)
        if p.exists():
            safe_print(f"--- listing {path} ---")
            for item in sorted(p.iterdir()):
                safe_print("  ", item.name, "(dir)" if item.is_dir() else "(file)")
        else:
            safe_print(f"--- path not found: {path} ---")
    except Exception:
        safe_print(f"--- could not list {path} ---")
        traceback.print_exc()

list_dir(".")
list_dir("AG116")
list_dir("AG116/backend")

# print environment variable NAMES that are present (not values)
safe_print("--- env var keys ---")
for k in sorted(os.environ.keys()):
    safe_print("  ", k)
safe_print("--- end env var keys ---")

# Attempt to import the FastAPI app; print full traceback on failure
try:
    safe_print("Attempting to import AG116.backend.server.app ...")
    # Use import_module to get clearer errors
    mod = import_module("AG116.backend.server")
    # Expect app attribute
    if hasattr(mod, "app"):
        safe_print("✅ Imported module AG116.backend.server — found attribute 'app'")
        app = getattr(mod, "app")
    else:
        safe_print("❌ Module imported but 'app' attribute NOT found on AG116.backend.server")
        safe_print("Module attributes:", sorted([a for a in dir(mod) if not a.startswith("__")]))
        raise RuntimeError("app attribute missing")
except Exception:
    safe_print("❌ Import-time exception while loading AG116.backend.server:", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    # re-raise so Vercel marks the function as crashed and shows the traceback
    raise

safe_print("=== wrapper import end ===")
