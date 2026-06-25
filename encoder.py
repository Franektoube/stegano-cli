"""High-performance multi-LSB encoder using NumPy vectorized operations."""

import numpy as np
from PIL import Image
from pathlib import Path
from utils import (
    validate_image_path, validate_bits, bytes_to_bits_array,
    build_header, calculate_capacity, format_size
)


def encode(
    image_path: str,
    file_path: str,
    output_path: str,
    bits_per_channel: int = 2,
    quiet: bool = False
) -> None:
    """Encode a file into an image using multi-LSB steganography."""

    bits_per_channel = validate_bits(bits_per_channel)
    img_path = validate_image_path(image_path)

    file_p = Path(file_path)
    if not file_p.exists():
        raise FileNotFoundError(f"File to encode not found: {file_path}")

    # Load image
    img = Image.open(img_path)
    if img.mode not in ('RGB', 'RGBA', 'L'):
        img = img.convert('RGB')

    pixels = np.array(img, dtype=np.uint8)

    if pixels.ndim == 2:
        h, w = pixels.shape
        num_channels = 1
        pixels = pixels.reshape(h, w, 1)
    else:
        h, w, num_channels = pixels.shape

    # Read file
    with open(file_p, 'rb') as f:
        file_data = f.read()

    filename = file_p.name

    # Build payload: header + file data
    header = build_header(file_data, filename, bits_per_channel)
    payload = header + file_data

    # Check capacity
    capacity = calculate_capacity(pixels.shape, num_channels, bits_per_channel)

    if len(payload) > capacity:
        raise ValueError(
            f"File too large! Need {format_size(len(payload))}, "
            f"but image can hold {format_size(capacity)} at {bits_per_channel} bits/channel."
        )

    if not quiet:
        print(f"Image: {w}x{h}, {num_channels} channels")
        print(f"Capacity at {bits_per_channel} bits/channel: {format_size(capacity)}")
        print(f"Payload size: {format_size(len(payload))} ({len(payload) / capacity * 100:.1f}% used)")
        print("Encoding...")

    # Convert payload to n-bit values
    values = bytes_to_bits_array(payload, bits_per_channel)

    # Flatten pixel array
    flat_pixels = pixels.flatten().copy()

    # FIX: maska musi być uint8 — & 0xFF przycina do 8 bitów
    mask = np.uint8((0xFF << bits_per_channel) & 0xFF)

    # Embed: clear LSBs then set new values
    num_values = len(values)
    flat_pixels[:num_values] = (flat_pixels[:num_values] & mask) | values

    # Reshape back
    result = flat_pixels.reshape(h, w, num_channels)

    if num_channels == 1:
        result = result.squeeze()

    # Save
    out_img = Image.fromarray(result, mode=img.mode)

    out_path = Path(output_path)
    if out_path.suffix.lower() not in ('.png', '.bmp', '.tiff', '.tif'):
        out_path = out_path.with_suffix('.png')

    out_img.save(str(out_path), compress_level=1)

    if not quiet:
        print(f"Encoded successfully → {out_path}")
        out_size = out_path.stat().st_size
        print(f"Output file size: {format_size(out_size)}")