"""Capacity analysis for steganographic images."""

import numpy as np
from PIL import Image
from utils import validate_image_path, calculate_capacity, format_size


def check_capacity(image_path: str, file_path: str = None) -> dict:
    """Check steganographic capacity of an image.
    
    Args:
        image_path: Path to carrier image
        file_path: Optional path to file to check fit
        
    Returns:
        Dictionary with capacity information
    """
    img_path = validate_image_path(image_path)
    
    img = Image.open(img_path)
    if img.mode not in ('RGB', 'RGBA', 'L'):
        img = img.convert('RGB')
    
    pixels = np.array(img, dtype=np.uint8)
    
    if pixels.ndim == 2:
        h, w = pixels.shape
        num_channels = 1
    else:
        h, w, num_channels = pixels.shape
    
    total_pixels = h * w
    total_values = total_pixels * num_channels
    
    result = {
        'image': str(img_path),
        'dimensions': f"{w}x{h}",
        'mode': img.mode,
        'channels': num_channels,
        'total_pixels': total_pixels,
        'total_values': total_values,
        'capacities': {}
    }
    
    file_size = None
    if file_path:
        from pathlib import Path
        fp = Path(file_path)
        if fp.exists():
            file_size = fp.stat().st_size
            result['file'] = str(fp)
            result['file_size'] = file_size
            result['file_size_human'] = format_size(file_size)
    
    for bits in range(1, 8):
        cap = calculate_capacity((h, w, num_channels), num_channels, bits)
        # Subtract max header overhead (~270 bytes)
        usable = max(0, cap - 270)
        
        entry = {
            'raw_bytes': cap,
            'usable_bytes': usable,
            'human': format_size(usable),
        }
        
        if file_size is not None:
            entry['fits'] = file_size <= usable
            entry['usage_percent'] = min(100.0, file_size / usable * 100) if usable > 0 else float('inf')
        
        result['capacities'][bits] = entry
    
    return result


def print_capacity_report(result: dict) -> None:
    """Print a formatted capacity report."""
    print(f"\n{'=' * 60}")
    print(f"  STEGANOGRAPHIC CAPACITY REPORT")
    print(f"{'=' * 60}")
    print(f"  Image:      {result['image']}")
    print(f"  Dimensions: {result['dimensions']}")
    print(f"  Mode:       {result['mode']} ({result['channels']} channel{'s' if result['channels'] > 1 else ''})")
    print(f"  Pixels:     {result['total_pixels']:,}")
    
    if 'file' in result:
        print(f"\n  Target file: {result['file']}")
        print(f"  File size:   {result['file_size_human']}")
    
    print(f"\n  {'Bits/Ch':<10} {'Capacity':<14} {'Quality Impact':<18}", end="")
    if 'file' in result:
        print(f" {'Fits?':<8} {'Usage':<10}", end="")
    print()
    print(f"  {'-' * 10} {'-' * 14} {'-' * 18}", end="")
    if 'file' in result:
        print(f" {'-' * 8} {'-' * 10}", end="")
    print()
    
    quality_labels = {
        1: "Imperceptible",
        2: "Very Low",
        3: "Low",
        4: "Moderate",
        5: "Noticeable",
        6: "High",
        7: "Very High",
    }
    
    for bits in range(1, 8):
        cap = result['capacities'][bits]
        line = f"  {bits:<10} {cap['human']:<14} {quality_labels[bits]:<18}"
        
        if 'file' in result:
            fits = "✓ YES" if cap.get('fits') else "✗ NO"
            usage = f"{cap.get('usage_percent', 0):.1f}%"
            line += f" {fits:<8} {usage:<10}"
        
        # Highlight recommended
        if 'file' in result and cap.get('fits'):
            min_bits = bits
        
        print(line)
    
    if 'file' in result:
        # Find minimum bits needed
        min_bits = None
        for bits in range(1, 8):
            if result['capacities'][bits].get('fits'):
                min_bits = bits
                break
        
        if min_bits:
            print(f"\n  ★ Recommended: {min_bits} bits/channel "
                  f"(best quality that fits your file)")
        else:
            print(f"\n  ✗ File is too large for this image at any bit depth!")
    
    print(f"{'=' * 60}\n")