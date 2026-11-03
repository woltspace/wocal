"""wocal serve | connect | disconnect."""

import argparse
import json
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

from wocal.server import DEFAULT_VOICE, STT_MODEL, TTS_MODEL, VOICES

DEFAULT_PORT = 4077


def _stop(message: str) -> int:
    print(f"wocal: {message}", file=sys.stderr)
    return 1


def _serve(args) -> int:
    if sys.platform != "darwin" or platform.machine() != "arm64":
        return _stop("this version needs an Apple Silicon Mac: the transcription model runs on mlx.")
    if shutil.which("ffmpeg") is None:
        return _stop("ffmpeg is missing. Install it with: brew install ffmpeg")
    import uvicorn

    uvicorn.run("wocal.server:app", host="127.0.0.1", port=args.port)  # this machine only
    return 0


def _lodge(*command: str) -> int:
    return subprocess.run(["woltspace", *command]).returncode


def _connect(args) -> int:
    if shutil.which("woltspace") is None:
        return _stop("woltspace is not on PATH, so there is no lodge to connect.")
    if args.voice not in VOICES:
        return _stop(f"unknown voice; one of {', '.join(sorted(VOICES))}")
    base = f"http://127.0.0.1:{args.port}"
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=5) as response:
            status = json.load(response)
    except (urllib.error.URLError, OSError, ValueError):
        return _stop(f"no Wocal server at {base}. Start it first.")
    if "failed" in status.values():
        return _stop(f"the server is up but a model failed to load: {status}")
    code = _lodge("transcription", "set", "--base-url", f"{base}/v1", "--model", STT_MODEL, "--no-key")
    if code == 0:
        code = _lodge("speech", "set", "--base-url", f"{base}/v1", "--model", TTS_MODEL,
                      "--voice", args.voice, "--no-key")
    return code


def _disconnect(_args) -> int:
    if shutil.which("woltspace") is None:
        return _stop("woltspace is not on PATH, so there is no lodge to disconnect.")
    return _lodge("transcription", "clear") or _lodge("speech", "clear")


def main() -> int:
    parser = argparse.ArgumentParser(prog="wocal", description="Local vocal wolts.")
    verbs = parser.add_subparsers(dest="verb", required=True)
    serve = verbs.add_parser("serve", help="run the server on this machine")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.set_defaults(run=_serve)
    connect = verbs.add_parser("connect", help="point this lodge's voice settings at the server")
    connect.add_argument("--port", type=int, default=DEFAULT_PORT)
    connect.add_argument("--voice", default=DEFAULT_VOICE)
    connect.set_defaults(run=_connect)
    disconnect = verbs.add_parser("disconnect", help="put this lodge's voice settings back to the defaults")
    disconnect.set_defaults(run=_disconnect)
    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
