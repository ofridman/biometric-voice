"""Command-line interface for the biometric voice recognition system."""

from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="biometric-voice",
        description="Biometric voice recognition – enroll, verify, and identify speakers.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- enroll --
    enroll = sub.add_parser("enroll", help="Enroll a new speaker")
    enroll.add_argument("name", help="Speaker name / identifier")
    enroll.add_argument("audio", help="Path to enrollment audio file (WAV)")

    # -- verify --
    verify = sub.add_parser("verify", help="Verify a speaker's identity")
    verify.add_argument("name", help="Enrolled speaker name")
    verify.add_argument("audio", help="Path to test audio file (WAV)")
    verify.add_argument(
        "-t", "--threshold", type=float, default=None,
        help="Cosine similarity threshold (default: 0.25)",
    )

    # -- identify --
    identify = sub.add_parser("identify", help="Identify who is speaking")
    identify.add_argument("audio", help="Path to test audio file (WAV)")
    identify.add_argument(
        "-t", "--threshold", type=float, default=None,
        help="Cosine similarity threshold (default: 0.25)",
    )

    # -- list --
    sub.add_parser("list", help="List enrolled speakers")

    # -- remove --
    remove = sub.add_parser("remove", help="Remove an enrolled speaker")
    remove.add_argument("name", help="Speaker name to remove")

    # -- record --
    record = sub.add_parser("record", help="Record audio from microphone")
    record.add_argument("output", help="Output WAV file path")
    record.add_argument(
        "-d", "--duration", type=float, default=5.0,
        help="Recording duration in seconds (default: 5)",
    )

    return parser


def _cmd_enroll(args: argparse.Namespace) -> None:
    from biometric_voice.speaker import SpeakerVerifier

    verifier = SpeakerVerifier()
    verifier.enroll(args.name, args.audio)
    print(f"Speaker '{args.name}' enrolled successfully.")


def _cmd_verify(args: argparse.Namespace) -> None:
    from biometric_voice.speaker import SpeakerVerifier

    verifier = SpeakerVerifier()
    match, score = verifier.verify(args.name, args.audio, threshold=args.threshold)
    status = "MATCH" if match else "NO MATCH"
    print(f"Result: {status}  (score: {score:.4f})")
    sys.exit(0 if match else 1)


def _cmd_identify(args: argparse.Namespace) -> None:
    from biometric_voice.speaker import SpeakerVerifier

    verifier = SpeakerVerifier()
    name, score = verifier.identify(args.audio, threshold=args.threshold)
    if name:
        print(f"Identified: {name}  (score: {score:.4f})")
    else:
        print(f"No match found.  (best score: {score:.4f})")
        sys.exit(1)


def _cmd_list(args: argparse.Namespace) -> None:
    from biometric_voice.speaker import SpeakerVerifier

    verifier = SpeakerVerifier()
    speakers = verifier.list_speakers()
    if speakers:
        print("Enrolled speakers:")
        for s in speakers:
            print(f"  - {s}")
    else:
        print("No speakers enrolled yet.")


def _cmd_remove(args: argparse.Namespace) -> None:
    from biometric_voice.speaker import SpeakerVerifier

    verifier = SpeakerVerifier()
    verifier.remove_speaker(args.name)
    print(f"Speaker '{args.name}' removed.")


def _cmd_record(args: argparse.Namespace) -> None:
    try:
        import sounddevice as sd
    except ImportError:
        print("Recording requires the 'sounddevice' package.")
        print("Install it with: pip install sounddevice")
        sys.exit(1)

    import numpy as np
    import soundfile as sf

    sample_rate = 16000
    print(f"Recording for {args.duration}s … speak now!")
    audio = sd.rec(
        int(args.duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    sf.write(args.output, audio, sample_rate)
    print(f"Saved to {args.output}")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    commands = {
        "enroll": _cmd_enroll,
        "verify": _cmd_verify,
        "identify": _cmd_identify,
        "list": _cmd_list,
        "remove": _cmd_remove,
        "record": _cmd_record,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
