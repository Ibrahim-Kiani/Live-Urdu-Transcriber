"""Standalone audio preprocessing test utility."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.services.audio_processing import prepare_audio


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare audio using the server preprocessing pipeline.")
    parser.add_argument("input", type=Path, help="Path to input audio file")
    parser.add_argument("output", type=Path, help="Path to output WAV file")
    parser.add_argument("--ratio", type=float, default=4.0, help="Compression ratio (default: 4.0)")
    parser.add_argument("--noise-gate-db", type=float, default=-50.0, help="Noise gate threshold in dBFS")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    if args.input.suffix.lower() not in {".wav"}:
        raise SystemExit("Only WAV input is supported with numpy/scipy processing.")

    audio_bytes = args.input.read_bytes()
    input_format = "wav"

    processed = prepare_audio(
        audio_bytes,
        input_format=input_format,
        noise_gate_db=args.noise_gate_db,
        compressor_ratio=args.ratio,
    )

    if not processed:
        raise SystemExit("No usable audio after preprocessing.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(processed)
    print(f"✅ Wrote processed audio to {args.output}")


if __name__ == "__main__":
    main()
