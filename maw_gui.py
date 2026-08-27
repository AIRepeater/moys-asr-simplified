# pyright: reportAny=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from maw.console import configure_utf8_stdio


_INTERNAL_FLAGS = frozenset(
    {
        "--smoke-import",
        "--transcribe",
    }
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Moy's ASR Workflow GUI")
    parser.add_argument("--smoke-import", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--transcribe",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-dbg",
        "--debug",
        action="store_true",
        help="开启 Launcher 的 pywebview 调试能力",
    )
    parser.add_argument(
        "-dt",
        "--devtools",
        action="store_true",
        help="启动 Launcher 后自动打开 DevTools（同时开启调试）",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    configure_utf8_stdio()
    raw_argv = list(sys.argv[1:] if argv is None else argv)

    args, rest = build_parser().parse_known_args(raw_argv)
    if args.smoke_import:
        return 0
    if args.transcribe:
        return _run_internal_transcribe(rest)

    from maw.gui_web import run_app

    run_app(debug=args.debug or args.devtools, devtools=args.devtools)
    return 0


def _run_internal_transcribe(argv: Sequence[str]) -> int:
    import generate_subtitle_qwen_api

    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_subtitle_qwen_api.py", *argv]
        result = generate_subtitle_qwen_api.main()
    finally:
        sys.argv = old_argv
    return 0 if result is None else int(result)


if __name__ == "__main__":
    raise SystemExit(main())
