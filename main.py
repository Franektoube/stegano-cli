#!/usr/bin/env python3
"""
LSB Steganography Tool — Hide files inside images using multi-bit LSB encoding.

Usage:
    Interactive:  python main.py
    Encode:       python main.py encode -i "C:\\Users\\photo.png" -f secret.zip -o output.png -b 2
    Decode:       python main.py decode -i "stego.png" -o ./extracted/
    Capacity:     python main.py capacity -i "image.png" -f secret.zip
"""

import argparse
import sys
import time


def clean_path(path: str) -> str:
    """Strip quotes and whitespace from a path string."""
    if path is None:
        return None
    return path.strip().strip('"').strip("'").strip()


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stego",
        description="🖼️ LSB Steganography Tool — Hide files inside images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                          Interactive mode
  %(prog)s encode -i "photo.png" -f secret.pdf -o out.png -b 2
  %(prog)s decode -i "out.png" -o ./extracted/
  %(prog)s capacity -i "photo.png" -f secret.pdf
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Encode
    enc = subparsers.add_parser("encode", aliases=["enc", "e"],
                                 help="Hide a file inside an image")
    enc.add_argument("-i", "--image", required=True, type=clean_path,
                     help="Carrier image (PNG/BMP/TIFF)")
    enc.add_argument("-f", "--file", required=True, type=clean_path,
                     help="File to hide")
    enc.add_argument("-o", "--output", required=True, type=clean_path,
                     help="Output image path")
    enc.add_argument("-b", "--bits", type=int, default=2,
                     help="Bits per channel (1-7, default: 2)")
    enc.add_argument("-q", "--quiet", action="store_true",
                     help="Suppress output")

    # Decode
    dec = subparsers.add_parser("decode", aliases=["dec", "d"],
                                 help="Extract a file from a steganographic image")
    dec.add_argument("-i", "--image", required=True, type=clean_path,
                     help="Steganographic image")
    dec.add_argument("-o", "--output-dir", default=".", type=clean_path,
                     help="Output directory (default: current)")
    dec.add_argument("-n", "--name", default=None, type=clean_path,
                     help="Override output filename")
    dec.add_argument("-q", "--quiet", action="store_true",
                     help="Suppress output")

    # Capacity
    cap = subparsers.add_parser("capacity", aliases=["cap", "c"],
                                 help="Check image capacity")
    cap.add_argument("-i", "--image", required=True, type=clean_path,
                     help="Image to analyze")
    cap.add_argument("-f", "--file", default=None, type=clean_path,
                     help="Optional: file to check if it fits")

    return parser


def main():
    parser = create_parser()

    if len(sys.argv) == 1:
        try:
            from cli import run_interactive
            run_interactive()
        except ImportError:
            print("Interactive mode requires InquirerPy:")
            print("  pip install InquirerPy")
            print()
            parser.print_help()
            sys.exit(1)
        return

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    start = time.perf_counter()

    try:
        if args.command in ("encode", "enc", "e"):
            from encoder import encode
            encode(
                image_path=args.image,
                file_path=args.file,
                output_path=args.output,
                bits_per_channel=args.bits,
                quiet=args.quiet,
            )

        elif args.command in ("decode", "dec", "d"):
            from decoder import decode
            decode(
                image_path=args.image,
                output_dir=args.output_dir,
                output_filename=args.name,
                quiet=args.quiet,
            )

        elif args.command in ("capacity", "cap", "c"):
            from capacity import check_capacity, print_capacity_report
            result = check_capacity(
                image_path=args.image,
                file_path=args.file,
            )
            print_capacity_report(result)

    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        raise

    elapsed = time.perf_counter() - start
    if not getattr(args, 'quiet', False):
        print(f"⏱️  Completed in {elapsed:.3f}s")


if __name__ == "__main__":
    main()