import os
import signal
import sys
import time
from datetime import datetime, timezone


def _read_heartbeat_seconds() -> float:
    raw = os.getenv("WORKER_HEARTBEAT_SECONDS", "2").strip()
    try:
        value = float(raw)
        if value <= 0:
            return 2.0
        return value
    except ValueError:
        return 2.0


running = True


def _handle_signal(_signum, _frame):
    global running
    running = False


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    heartbeat = _read_heartbeat_seconds()
    print("[worker] Placeholder worker started", flush=True)
    print(f"[worker] heartbeat_interval_seconds={heartbeat}", flush=True)

    while running:
        ts = datetime.now(timezone.utc).isoformat()
        print(f"[worker] heartbeat {ts}", flush=True)
        time.sleep(heartbeat)

    print("[worker] Placeholder worker stopped", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
