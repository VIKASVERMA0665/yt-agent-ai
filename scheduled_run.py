"""Run one scheduled Bhakti Dhun upload. Intended for Windows Task Scheduler."""
import argparse
import os
import traceback
from datetime import datetime
from contextlib import redirect_stdout, redirect_stderr

from pipeline import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-type", choices=("shorts", "normal"), required=True)
    parser.add_argument("--slot", default="scheduled")
    args = parser.parse_args()

    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", f"{datetime.now():%Y-%m-%d}_{args.slot}.log")
    with open(log_path, "a", encoding="utf-8", buffering=1) as log:
        with redirect_stdout(log), redirect_stderr(log):
            print(f"\n=== START {datetime.now().isoformat()} type={args.video_type} slot={args.slot} ===")
            try:
                run(video_type=args.video_type, auto_upload=True, voice="hi-IN-MadhurNeural")
            except Exception:
                traceback.print_exc()
                raise
            finally:
                print(f"=== END {datetime.now().isoformat()} ===")


if __name__ == "__main__":
    main()
