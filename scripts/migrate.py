"""
Run Alembic migrations to the latest revision.
Usage:
    python scripts/migrate.py            # upgrade to head
    python scripts/migrate.py downgrade  # downgrade one step
    python scripts/migrate.py current    # show current revision
    python scripts/migrate.py history    # show migration history
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ussop"))

from alembic.config import Config
from alembic import command


def main():
    cfg = Config(str(ROOT / "alembic.ini"))
    cmd = sys.argv[1] if len(sys.argv) > 1 else "upgrade"

    if cmd == "upgrade":
        print("[migrate] Upgrading to head…")
        command.upgrade(cfg, "head")
        print("[migrate] Done.")
    elif cmd == "downgrade":
        print("[migrate] Downgrading one step…")
        command.downgrade(cfg, "-1")
        print("[migrate] Done.")
    elif cmd == "current":
        command.current(cfg)
    elif cmd == "history":
        command.history(cfg, verbose=True)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
