"""
Build the React frontend and output to ussop/static/dist/.
Run from project root: python scripts/build_frontend.py
"""
import subprocess
import sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent.parent / "ussop" / "frontend"
DIST_DIR = Path(__file__).parent.parent / "ussop" / "static" / "dist"


def main():
    if not FRONTEND_DIR.exists():
        print(f"[build_frontend] Frontend not found at {FRONTEND_DIR}")
        sys.exit(1)

    print("[build_frontend] Installing npm dependencies...")
    subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)

    print("[build_frontend] Building React SPA...")
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True)

    if (DIST_DIR / "index.html").exists():
        print(f"[build_frontend] ✓ Built to {DIST_DIR}")
    else:
        print("[build_frontend] ✗ Build completed but index.html not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
