#!/usr/bin/env python3
"""Ship a product from the terminal and get its files in your workspace.

The IDE workflow: instead of previewing in the Studio UI, the team's output
lands as real files you can open, run, and iterate on with your IDE agent.

    uv run python cli.py "A pomodoro timer with a session log" -o ./pomodoro
    uv run python cli.py "..." --server https://studio-xxxx.run.app

The CLI talks to the Studio's public /api/build_stream endpoint, so it works
against both a local team (run_local.sh) and the deployed one.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

STATUS_ICONS = {"pass": "✅", "fail": "❌"}


def safe_relative_path(path: str) -> str | None:
    """Mirrors the Studio's path rules: relative, no traversal."""
    path = path.strip()
    while path.startswith("./"):
        path = path[2:]
    if not path or path.startswith(("/", "\\")) or ".." in path.split("/"):
        return None
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("idea", help="What the team should build")
    parser.add_argument(
        "-o", "--out", default="./product", help="Directory to write the app files into"
    )
    parser.add_argument(
        "--server",
        default=os.environ.get("TEAM_STUDIO_URL", "http://localhost:8000"),
        help="Studio base URL (default: $TEAM_STUDIO_URL or http://localhost:8000)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    server = args.server.rstrip("/")
    files = None
    raw = None

    print(f"🎯 Sending the idea to the team at {server} ...")
    try:
        with httpx.Client(timeout=httpx.Timeout(600.0, connect=15.0)) as client:
            with client.stream(
                "POST", f"{server}/api/build_stream", json={"message": args.idea}
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    etype = event.get("type")
                    if etype == "status":
                        print(event["text"])
                    elif etype == "plan":
                        pass  # streamed repeatedly; the final files are what we keep
                    elif etype == "review":
                        icon = STATUS_ICONS.get(event.get("status"), "❔")
                        print(
                            f"{icon} Review iteration {event['iteration']}: "
                            f"{event.get('status', 'unknown')} — {event.get('feedback', '')}"
                        )
                    elif etype == "result":
                        files = event.get("files")
                        raw = event.get("raw")
    except httpx.HTTPError as exc:
        print(f"💥 Could not reach the team: {exc}", file=sys.stderr)
        return 1

    if not files:
        print("💥 The team did not ship usable files.", file=sys.stderr)
        if raw:
            print("--- raw builder output ---\n" + raw[:2000], file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    for path, content in files.items():
        rel = safe_relative_path(path)
        if rel is None:
            print(f"⚠️ Skipping unsafe path from builder: {path!r}", file=sys.stderr)
            continue
        target = out_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"📄 {target} ({len(content):,} bytes)")

    print(f"\n🚢 Shipped to {out_dir}/ — open {out_dir / 'index.html'} in a browser,")
    print("   or point your IDE agent at the directory to keep building.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
