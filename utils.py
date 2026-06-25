"""Utility functions and constants for LSB steganography."""

import numpy as np
from pathlib import Path

MAGIC = b"STEG"
HEADER_SIZE = 4 + 4 + 1 + 4  # magic(4) + file_size(4) + bits_per_channel(1) + filename_len(4)


def validate_image_path(path: str) -> Path:
    """Validate that image path exists and is a supported format."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if p.suffix.lower() not in ('.png', '.bmp', '.tiff', '.tif'):
        raise ValueError(f"Unsupported image format: {p.suffix}. Use PNG, BMP, or TIFF.")
    return p


def validate_bits(bits: int) -> int:
    """Validate bits per channel value."""
    if not 1 <= bits <= 7:
        raise ValueError(f"Bits per channel must be 1-7, got {bits}")
    return bits


def bytes_to_bits_array(data: bytes, bits_per_channel: int) -> np.ndarray:
    """Convert bytes to array of n-bit values packed for embedding.

    Each byte is split into chunks of `bits_per_channel` bits.
    Uses uint16 intermediate to prevent overflow.
    """
    byte_arr = np.frombuffer(data, dtype=np.uint8)
    # Unpack all bytes into individual bits
    all_bits = np.unpackbits(byte_arr)

    # Pad to multiple of bits_per_channel
    remainder = len(all_bits) % bits_per_channel
    if remainder:
        padding = bits_per_channel - remainder
        all_bits = np.concatenate([all_bits, np.zeros(padding, dtype=np.uint8)])

    # Reshape into groups of bits_per_channel
    num_values = len(all_bits) // bits_per_channel
    groups = all_bits[:num_values * bits_per_channel].reshape(num_values, bits_per_channel)

    # Convert each group to an integer value
    # Use uint16 to prevent overflow during computation
    powers = (1 << np.arange(bits_per_channel - 1, -1, -1, dtype=np.uint16))
    values = (groups.astype(np.uint16) * powers).sum(axis=1).astype(np.uint8)

    return values


def bits_array_to_bytes(values: np.ndarray, bits_per_channel: int, num_bytes: int) -> bytes:
    """Convert array of n-bit values back to bytes.

    Extracts individual bits from each value then packs into bytes.
    """
    num_values = len(values)
    total_bit_slots = num_values * bits_per_channel

    # Pre-allocate bit array
    all_bits = np.zeros(total_bit_slots, dtype=np.uint8)

    # Extract bits from each value (MSB first within each group)
    vals16 = values.astype(np.uint16)
    for i in range(bits_per_channel):
        shift = bits_per_channel - 1 - i
        all_bits[i::bits_per_channel] = (vals16 >> shift) & 1

    # Trim to exact number of bits needed
    total_bits_needed = num_bytes * 8
    if total_bit_slots < total_bits_needed:
        raise ValueError(f"Not enough data: have {total_bit_slots} bits, need {total_bits_needed}")

    all_bits = all_bits[:total_bits_needed]

    # Pad to multiple of 8 if needed
    remainder = len(all_bits) % 8
    if remainder:
        all_bits = np.concatenate([all_bits, np.zeros(8 - remainder, dtype=np.uint8)])

    # Pack bits into bytes
    packed = np.packbits(all_bits)
    return packed[:num_bytes].tobytes()


def build_header(file_data: bytes, filename: str, bits_per_channel: int) -> bytes:
    """Build header for embedded data."""
    fname_bytes = filename.encode('utf-8')
    header = bytearray()
    header.extend(MAGIC)
    header.extend(len(file_data).to_bytes(4, 'big'))
    header.extend(bits_per_channel.to_bytes(1, 'big'))
    header.extend(len(fname_bytes).to_bytes(4, 'big'))
    header.extend(fname_bytes)
    return bytes(header)


def parse_header(data: bytes):
    """Parse header from extracted data.

    Returns (file_size, bits_per_channel, filename, header_total_len).
    """
    if len(data) < 13:
        raise ValueError("Data too short to contain header.")
    if data[:4] != MAGIC:
        raise ValueError("No steganographic data found (invalid magic bytes).")

    file_size = int.from_bytes(data[4:8], 'big')
    bits_per_channel = data[8]
    fname_len = int.from_bytes(data[9:13], 'big')

    if fname_len > 1024:
        raise ValueError(f"Filename length {fname_len} seems corrupted.")

    header_end = 13 + fname_len
    if len(data) < header_end:
        raise ValueError("Data too short for filename.")

    filename = data[13:header_end].decode('utf-8')
    return file_size, bits_per_channel, filename, header_end


def calculate_capacity(image_shape: tuple, num_channels: int, bits_per_channel: int) -> int:
    """Calculate how many bytes can be stored in the image."""
    h, w = image_shape[:2]
    total_values = h * w * num_channels
    total_data_bits = total_values * bits_per_channel
    total_data_bytes = total_data_bits // 8
    return total_data_bytes


def format_size(size_bytes: int) -> str:
    """Format byte size to human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"