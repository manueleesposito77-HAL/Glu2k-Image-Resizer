"""Generate a simple app icon for Glu2k-Image-Resizer"""
from PIL import Image, ImageDraw, ImageFont

sizes = [16, 32, 48, 64, 128, 256]
images = []

for size in sizes:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded rectangle
    margin = max(1, size // 16)
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=max(2, size // 8),
        fill=(30, 30, 46),
        outline=(137, 180, 250),
        width=max(1, size // 32)
    )

    # Draw compress arrows
    cx, cy = size // 2, size // 2
    s = size // 4

    # Top arrow pointing down
    draw.polygon([
        (cx, cy - s // 3),
        (cx - s // 2, cy - s),
        (cx + s // 2, cy - s)
    ], fill=(166, 227, 161))

    # Bottom arrow pointing up
    draw.polygon([
        (cx, cy + s // 3),
        (cx - s // 2, cy + s),
        (cx + s // 2, cy + s)
    ], fill=(137, 180, 250))

    images.append(img)

images[0].save("icon.ico", format="ICO", sizes=[(s, s) for s in sizes],
               append_images=images[1:])
print("icon.ico created")
