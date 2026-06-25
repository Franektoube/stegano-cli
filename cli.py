"""Interactive CLI interface using InquirerPy."""

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator
from InquirerPy.validator import PathValidator
from prompt_toolkit.validation import Validator, ValidationError
import sys
import os
from pathlib import Path


def clean_path(path: str) -> str:
    """Strip quotes and whitespace from path."""
    return path.strip().strip('"').strip("'").strip()


class CleanPathValidator(Validator):
    """Path validator that strips quotes before checking."""

    def __init__(self, is_file: bool = False, is_dir: bool = False, message: str = "Invalid path"):
        self.is_file = is_file
        self.is_dir = is_dir
        self.message = message

    def validate(self, document):
        path = clean_path(document.text)
        p = Path(path)
        if self.is_file and not p.is_file():
            raise ValidationError(message=self.message, cursor_position=len(document.text))
        if self.is_dir and not p.is_dir():
            raise ValidationError(message=self.message, cursor_position=len(document.text))


def ask_filepath(message: str, qmark: str = "📄") -> str:
    """Ask for a file path, accepting quoted paths like \"C:\\Users\\...\\file.png\"."""
    raw = inquirer.text(
        message=message,
        qmark=qmark,
        validate=CleanPathValidator(is_file=True, message="File does not exist (you can use quotes around path)"),
        filter=clean_path,
    ).execute()
    return raw


def ask_dirpath(message: str, default: str = ".", qmark: str = "📁") -> str:
    """Ask for a directory path, accepting quoted paths."""
    raw = inquirer.text(
        message=message,
        default=default,
        qmark=qmark,
        filter=clean_path,
    ).execute()
    return raw


def get_action() -> str:
    """Ask user what they want to do."""
    action = inquirer.select(
        message="What would you like to do?",
        choices=[
            Choice(value="encode", name="🔒 Encode — Hide a file in an image"),
            Choice(value="decode", name="🔓 Decode — Extract a file from an image"),
            Choice(value="capacity", name="📊 Capacity — Check how much data an image can hold"),
            Separator(),
            Choice(value="exit", name="🚪 Exit"),
        ],
        default="encode",
        pointer="▸",
        qmark="🖼️",
    ).execute()
    return action


def get_encode_params() -> dict:
    """Get parameters for encoding."""
    print()

    image_path = ask_filepath("Carrier image path (PNG/BMP/TIFF):", qmark="📷")
    file_path = ask_filepath("File to hide:", qmark="📄")

    # Show quick capacity check
    try:
        from capacity import check_capacity
        result = check_capacity(image_path, file_path)

        choices = []
        for bits in range(1, 8):
            cap = result['capacities'][bits]
            fits = cap.get('fits', True)
            label = f"{bits} bit{'s' if bits > 1 else ''}/channel — capacity: {cap['human']}"
            if not fits:
                label += " (TOO SMALL)"
            choices.append(Choice(value=bits, name=label, enabled=fits))

        recommended = 2
        for bits in range(1, 8):
            if result['capacities'][bits].get('fits', True):
                recommended = bits
                break

    except Exception:
        choices = [Choice(value=i, name=f"{i} bit{'s' if i > 1 else ''}/channel") for i in range(1, 8)]
        recommended = 2

    bits = inquirer.select(
        message="Bits per channel (more = more capacity, less quality):",
        choices=choices,
        default=recommended,
        qmark="⚙️",
        pointer="▸",
    ).execute()

    default_output = str(Path(image_path).stem + "_stego.png")

    output_path = inquirer.text(
        message="Output image path:",
        default=default_output,
        qmark="💾",
        filter=clean_path,
    ).execute()

    if os.path.exists(output_path):
        overwrite = inquirer.confirm(
            message=f"{output_path} already exists. Overwrite?",
            default=False,
            qmark="⚠️",
        ).execute()
        if not overwrite:
            print("Cancelled.")
            return None

    return {
        'image_path': image_path,
        'file_path': file_path,
        'output_path': output_path,
        'bits_per_channel': bits,
    }


def get_decode_params() -> dict:
    """Get parameters for decoding."""
    print()

    image_path = ask_filepath("Steganographic image path:", qmark="🖼️")
    output_dir = ask_dirpath("Output directory:", default=".", qmark="📁")

    custom_name = inquirer.confirm(
        message="Use custom output filename?",
        default=False,
        qmark="✏️",
    ).execute()

    output_filename = None
    if custom_name:
        output_filename = inquirer.text(
            message="Output filename:",
            qmark="📝",
            filter=clean_path,
        ).execute()

    return {
        'image_path': image_path,
        'output_dir': output_dir,
        'output_filename': output_filename,
    }


def get_capacity_params() -> dict:
    """Get parameters for capacity check."""
    print()

    image_path = ask_filepath("Image path to analyze:", qmark="📷")

    check_file = inquirer.confirm(
        message="Check if a specific file would fit?",
        default=False,
        qmark="📄",
    ).execute()

    file_path = None
    if check_file:
        file_path = ask_filepath("File to check:", qmark="📄")

    return {
        'image_path': image_path,
        'file_path': file_path,
    }


def run_interactive():
    """Run the interactive CLI loop."""
    print()
    print("╔══════════════════════════════════════════╗")
    print("║   🖼️  LSB Steganography Tool             ║")
    print("║   Hide files inside images               ║")
    print("╚══════════════════════════════════════════╝")
    print()

    while True:
        try:
            action = get_action()

            if action == "exit":
                print("\nBye! 👋\n")
                sys.exit(0)

            elif action == "encode":
                params = get_encode_params()
                if params is None:
                    continue

                print()
                from encoder import encode
                try:
                    encode(**params)
                except Exception as e:
                    print(f"\n❌ Error: {e}\n")

            elif action == "decode":
                params = get_decode_params()

                print()
                from decoder import decode
                try:
                    decode(**params)
                except Exception as e:
                    print(f"\n❌ Error: {e}\n")

            elif action == "capacity":
                params = get_capacity_params()

                from capacity import check_capacity, print_capacity_report
                try:
                    result = check_capacity(**params)
                    print_capacity_report(result)
                except Exception as e:
                    print(f"\n❌ Error: {e}\n")

            print()

            again = inquirer.confirm(
                message="Do something else?",
                default=True,
                qmark="🔄",
            ).execute()

            if not again:
                print("\nBye! 👋\n")
                break

            print()

        except KeyboardInterrupt:
            print("\n\nBye! 👋\n")
            sys.exit(0)