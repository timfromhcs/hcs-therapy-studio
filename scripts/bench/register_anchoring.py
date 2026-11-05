"""Measure whether register anchoring actually holds, against the real model.

This is not a unit test: it needs a running server and the 1.7 GB model. It is a
measurement script, so it lives in scripts/ and refuses to fake anything — if the
server is down it says so and exits non-zero.

    hcs-therapy serve --port 8765 --start-backend
    .\\.venv\\Scripts\\python.exe scripts\\bench\\register_anchoring.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8765"
TOKEN_FILE = pathlib.Path.home() / "AppData" / "Local" / "HCS" / "TherapyStudio" / "api-token.txt"

PROMPTS = [
    ("du", "Kannst du mir helfen, abends besser runterzukommen? Ich schlafe schlecht."),
    ("sie", "Können Sie mir bitte erklären, wie ich abends besser zur Ruhe komme?"),
    ("du", "Ich habe Angst vor der Prüfung und weiss nicht weiter. Was meinst du?"),
    ("sie", "Ich habe Angst vor der Prüfung. Was raten Sie mir?"),
    ("none", "Ich habe schlecht geschlafen und mache mir Sorgen über die Arbeit."),
]


def token() -> str:
    if not TOKEN_FILE.is_file():
        raise SystemExit(f"no API token at {TOKEN_FILE}; start `hcs-therapy serve` first")
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


def ask(tok: str, message: str, *, anchor_disabled: bool = False, max_tokens: int = 220) -> dict:
    body = {
        "messages": [{"role": "user", "content": message}],
        "max_tokens": max_tokens,
        "temperature": 0.4,
    }
    if anchor_disabled:
        body["hcs"] = {"no_register_anchor": True}
    request = urllib.request.Request(
        f"{BASE}/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310 loopback
        payload = json.loads(response.read())
    payload["_text"] = payload["choices"][0]["message"]["content"]
    return payload


def main(argv: list[str] | None = None) -> int:
    import argparse

    # Model output contains characters a legacy Windows code page cannot encode.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ab",
        action="store_true",
        help="run both arms (anchored and unanchored) and report the difference",
    )
    parser.add_argument("--max-tokens", type=int, default=220)
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="repeat the prompt set N times; n=5 is too small to quote a rate from",
    )
    args = parser.parse_args(argv)

    try:
        tok = token()
        urllib.request.urlopen(f"{BASE}/health", timeout=5)  # noqa: S310 loopback
    except (urllib.error.URLError, OSError) as exc:
        print(f"server not reachable on {BASE}: {exc}", file=sys.stderr)
        return 1

    def run(disabled: bool) -> tuple[list[dict], dict[str, int]]:
        rows: list[dict] = []
        stats = {"mixed": 0, "wrong_register": 0, "neutral_no_signal": 0, "requests": 0}
        for _ in range(max(1, args.repeat)):
            for expected, prompt in PROMPTS:
                payload = ask(tok, prompt, anchor_disabled=disabled, max_tokens=args.max_tokens)
                register = payload.get("hcs", {}).get("register", {})
                detected = register.get("register")
                is_mixed = bool(register.get("mixed"))
                stats["requests"] += 1
                stats["mixed"] += is_mixed
                if expected in ("du", "sie"):
                    if detected != expected:
                        stats["wrong_register"] += 1
                elif detected is None or detected == "neutral":
                    stats["neutral_no_signal"] += 1
                rows.append(
                    {
                        "expected": expected,
                        "detected": detected,
                        "du": register.get("du_forms"),
                        "sie": register.get("sie_forms"),
                        "mixed": is_mixed,
                        # "none" means the prompt carried no register signal, so no
                        # verdict of its own is expected; scoring it as a mismatch
                        # would make the summary look worse than the data is.
                        "matches_expected": is_mixed is False
                        and (expected == "none" or detected == expected),
                        "anchored": register.get("anchored"),
                        "chars": len(payload["_text"]),
                        "sample": payload["_text"][:120].replace("\n", " "),
                    }
                )
        return rows, stats

    if not args.ab:
        rows, stats = run(False)
    else:
        anchored_rows, anchored_stats = run(False)
        plain_rows, plain_stats = run(True)
        rows = anchored_rows
        stats = anchored_stats
        report = {
            "requests_per_arm": anchored_stats["requests"],
            "anchored": {"stats": anchored_stats, "rows": anchored_rows},
            "unanchored": {"stats": plain_stats, "rows": plain_rows},
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        print(
            f"\nn={anchored_stats['requests']} pro Arm. "
            f"Anrede gewechselt: {anchored_stats['mixed']} mit Anker, "
            f"{plain_stats['mixed']} ohne. "
            f"Falsche Anrede: {anchored_stats['wrong_register']} mit Anker, "
            f"{plain_stats['wrong_register']} ohne.",
            file=sys.stderr,
        )
        return 0 if anchored_stats["wrong_register"] == 0 and anchored_stats["mixed"] == 0 else 2

    print(
        json.dumps(
            {"stats": stats, "rows": rows}, indent=2, ensure_ascii=False
        )
    )
    print(
        f"\n{stats['mixed']} von {stats['requests']} Antworten wechselten die Anrede; "
        f"{stats['wrong_register']} hatten die falsche Anrede.",
        file=sys.stderr,
    )
    return 0 if stats["mixed"] == 0 and stats["wrong_register"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
