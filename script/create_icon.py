"""
Create a simple ICO icon for vnpy_autorepay
"""

import struct

def create_icon():
    """Create a simple ICO file"""
    # ICO file header
    # Reserved (2 bytes) + Type (2 bytes) + Count (2 bytes)
    header = struct.pack('<HHH', 0, 1, 1)
    
    # Icon directory entry
    # Width, Height, ColorCount, Reserved, Planes, BitCount, BytesInRes, ImageOffset
    dir_entry = struct.pack('<BBBBHHLL', 32, 32, 0, 0, 1, 32, 0, 22)
    
    # Create a simple 32x32 32-bit RGBA icon
    # We'll create a gradient pattern
    pixels = []
    for y in range(32):
        for x in range(32):
            # Create a simple gradient + circle pattern
            dx = x - 16
            dy = y - 16
            dist = (dx*dx + dy*dy)**0.5
            
            if dist < 12:
                # Inside circle - blue gradient
                alpha = 255
                r = 50 + int(100 * (1 - dist/12))
                g = 100 + int(100 * (1 - dist/12))
                b = 200 + int(55 * (1 - dist/12))
            else:
                # Outside circle - transparent
                r, g, b, alpha = 0, 0, 0, 0
            
            pixels.extend([b, g, r, alpha])
    
    raw_data = bytes(pixels)
    
    # Calculate BITMAPINFOHEADER
    # Size, Width, Height, Planes, BitCount, Compression, SizeImage, XPelsPerMeter, YPelsPerMeter, ClrUsed, ClrImportant
    info_header = struct.pack('<LllHHLLllLL', 40, 32, 64, 1, 32, 0, len(raw_data), 0, 0, 0, 0)
    
    # Combine all parts
    icon_data = header + dir_entry + info_header + raw_data
    
    # Write to file
    with open('autorepay.ico', 'wb') as f:
        f.write(icon_data)
    
    print("Created autorepay.ico successfully!")

if __name__ == "__main__":
    create_icon()
