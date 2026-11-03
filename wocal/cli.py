"""wocal serve."""

import argparse
import platform
import shutil
import sys

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


def main() -> int:
    parser = argparse.ArgumentParser(prog="wocal", description="Local vocal wolts.")
    verbs = parser.add_subparsers(dest="verb", required=True)
    serve = verbs.add_parser("serve", help="run the server on this machine")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.set_defaults(run=_serve)
    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
