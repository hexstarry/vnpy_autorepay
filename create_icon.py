"""
生成 autorepay.ico 图标文件
"""

import struct
import zlib

def create_ico_file(filename: str, size: int = 32):
    """创建一个简单的 ICO 文件"""
    
    # ICO 文件头
    icon_dir = struct.pack('<HHH', 0, 1, 1)  # reserved, type (1=ICO), count
    
    # 图标目录条目
    icon_dir_entry = struct.pack('<BBBBHHII',
        size,      # width
        size,      # height
        0,         # color count (0 if >= 8bpp)
        0,         # reserved
        1,         # color planes
        32,        # bits per pixel
        0,         # size of image data (will be filled later)
        0          # offset of image data (will be filled later)
    )
    
    # 创建一个简单的 32x32 RGBA 图像数据
    # 使用蓝色渐变圆形图案
    width = size
    height = size
    
    # BMP 信息头 (BITMAPINFOHEADER)
    bmp_info_header = struct.pack('<IiiHHIIiiII',
        40,        # header size
        width,     # width
        height * 2,  # height (doubled for ICO format)
        1,         # planes
        32,        # bits per pixel (RGBA)
        0,         # compression (none)
        0,         # image size (can be 0 for uncompressed)
        0,         # x pixels per meter
        0,         # y pixels per meter
        0,         # colors used
        0          # important colors
    )
    
    # 创建像素数据 (从下到上，BGRA 格式)
    pixels = []
    center_x = width // 2
    center_y = height // 2
    radius = min(center_x, center_y) - 2
    
    for y in range(height):
        for x in range(width):
            # 计算到中心的距离
            dx = x - center_x
            dy = y - center_y
            dist = (dx * dx + dy * dy) ** 0.5
            
            if dist <= radius:
                # 在圆形内 - 蓝色渐变
                intensity = 1.0 - (dist / radius) * 0.5
                # 从中心蓝色到边缘浅蓝色
                blue = int(255 * intensity)
                green = int(100 * intensity)
                red = int(50 * intensity)
                alpha = 255
            else:
                # 圆形外 - 透明
                blue = 0
                green = 0
                red = 0
                alpha = 0
            
            # BGRA 格式
            pixels.append(struct.pack('BBBB', blue, green, red, alpha))
    
    # 组合图像数据
    image_data = bmp_info_header + b''.join(pixels)
    
    # 更新目录条目中的大小和偏移
    icon_dir_entry = struct.pack('<BBBBHHII',
        size, size, 0, 0, 1, 32,
        len(image_data),
        6 + 16  # 文件头 + 目录条目大小
    )
    
    # 组合完整的 ICO 文件
    ico_data = icon_dir + icon_dir_entry + image_data
    
    # 写入文件
    with open(filename, 'wb') as f:
        f.write(ico_data)
    
    print(f"图标文件已创建: {filename}")
    print(f"尺寸: {size}x{size} 像素")
    print(f"文件大小: {len(ico_data)} 字节")

if __name__ == "__main__":
    create_ico_file("vnpy_autorepay/ui/autorepay.ico", 32)