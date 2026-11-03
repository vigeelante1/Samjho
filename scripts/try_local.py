"""Test the pipeline on files without Telegram.

Usage:
    python -m scripts.try_local samples/bill.jpg
    python -m scripts.try_local samples/notice.pdf --lang en --json
"""
import argparse
import json
import mimetypes
from pathlib import Path

from app.pipeline import explain


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+")
    p.add_argument("--lang", default="hi", choices=["hi", "en"])
    p.add_argument("--json", action="store_true", help="also print the verified JSON")
    args = p.parse_args()

    for f in args.files:
        path = Path(f)
        print(f"\n===== {path.name} =====")
        out = explain(path.read_bytes(), path.name, mimetypes.guess_type(path.name)[0] or "", args.lang)
        print(out["message"])
        if args.json:
            print(json.dumps(out["result"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
