"""High-performance multi-LSB decoder using NumPy vectorized operations."""

import numpy as np
from PIL import Image
from pathlib import Path
from utils import (
    validate_image_path, bits_array_to_bytes, parse_header,
    HEADER_SIZE, format_size
)


def decode(
    image_path: str,
    output_dir: str = ".",
    output_filename: str = None,
    quiet: bool = False
) -> str:
    """Decode a file from a steganographic image.
    
    First extracts header at 1 bit/channel to determine parameters,
    then extracts full payload at the correct bit depth.
    
    Args:
        image_path: Path to steganographic image
        output_dir: Directory to save extracted file
        output_filename: Override extracted filename
        quiet: Suppress output
        
    Returns:
        Path to extracted file
    """
    img_path = validate_image_path(image_path)
    
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
    
    flat_pixels = pixels.flatten()
    
    if not quiet:
        print(f"Image: {w}x{h}, {num_channels} channels")
        print("Extracting header...")
    
    # Step 1: We need to figure out bits_per_channel.
    # The header always stores bits_per_channel at byte offset 8.
    # But the header itself is encoded with that same bits_per_channel.
    # We need to try different bit depths to find valid magic.
    
    bits_per_channel = None
    header_data = None
    
    for try_bits in range(1, 8):
        # Extract enough values for a reasonable header (assume max filename 256 chars)
        max_header_bytes = HEADER_SIZE + 256
        num_values_needed = (max_header_bytes * 8 + try_bits - 1) // try_bits
        
        if num_values_needed > len(flat_pixels):
            continue
        
        # Extract LSBs
        mask = np.uint8((1 << try_bits) - 1)
        extracted = flat_pixels[:num_values_needed] & mask
        
        # Convert to bytes
        try:
            candidate = bits_array_to_bytes(extracted, try_bits, max_header_bytes)
            if candidate[:4] == b"STEG":
                bits_per_channel = try_bits
                header_data = candidate
                break
        except Exception:
            continue
    
    if bits_per_channel is None:
        raise ValueError("No steganographic data found in this image.")
    
    if not quiet:
        print(f"Detected encoding: {bits_per_channel} bits/channel")
    
    # Step 2: Parse header
    file_size, stored_bits, filename, header_total_len = parse_header(header_data)
    
    if not quiet:
        print(f"Embedded file: {filename}")
        print(f"File size: {format_size(file_size)}")
    
    # Step 3: Extract full payload
    total_payload_bytes = header_total_len + file_size
    num_values_needed = (total_payload_bytes * 8 + bits_per_channel - 1) // bits_per_channel
    
    if num_values_needed > len(flat_pixels):
        raise ValueError("Image doesn't contain enough data (corrupted or truncated).")
    
    mask = np.uint8((1 << bits_per_channel) - 1)
    extracted = flat_pixels[:num_values_needed] & mask
    
    all_data = bits_array_to_bytes(extracted, bits_per_channel, total_payload_bytes)
    
    # Extract file data (skip header)
    file_data = all_data[header_total_len:header_total_len + file_size]
    
    if len(file_data) != file_size:
        raise ValueError(f"Data size mismatch: expected {file_size}, got {len(file_data)}")
    
    # Save file
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_name = output_filename if output_filename else filename
    out_path = out_dir / out_name
    
    # Avoid overwriting
    if out_path.exists():
        stem = out_path.stem
        suffix = out_path.suffix
        counter = 1
        while out_path.exists():
            out_path = out_dir / f"{stem}_{counter}{suffix}"
            counter += 1
    
    with open(out_path, 'wb') as f:
        f.write(file_data)
    
    if not quiet:
        print(f"Decoded successfully → {out_path}")
    
    return str(out_path)