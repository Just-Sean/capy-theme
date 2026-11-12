"""GIF builders shared by the image tests."""

import io
import struct

from PIL import Image


def gif(frames=1, comment=b"", duration=100, loop=None, transparent=False):
    """A GIF made with Pillow. Its frames are clearly different, since Pillow
    merges identical ones."""
    colors = [(255, 0, 0), (0, 128, 0), (0, 0, 255)]
    colors = [colors[i] if i < 3 else (i % 256, i // 256, 128) for i in range(frames)]
    if transparent:  # a colored square on a transparent background
        images = []
        for color in colors:
            frame = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
            frame.paste(Image.new("RGBA", (5, 5), (*color, 255)), (0, 0))
            images.append(frame)
    else:
        images = [Image.new("RGB", (10, 10), color) for color in colors]
    extra = {} if loop is None else {"loop": loop}
    buffer = io.BytesIO()
    images[0].save(
        buffer,
        "GIF",
        save_all=frames > 1,
        append_images=images[1:],
        comment=comment,
        duration=duration,
        **extra,
    )
    return buffer.getvalue()


def hand_built_gif(canvas, frames, trailer=True):
    """A GIF built byte by byte: a canvas × canvas image, then one frame per entry
    in `frames`, each (width, height) or (width, height, left, top). Every frame
    holds a single pixel of data, so the file stays tiny whatever the sizes it
    states (a frame bigger than 1 × 1 is cut short)."""
    data = b"GIF89a" + struct.pack("<HHBBB", canvas, canvas, 0x80, 0, 0)
    data += b"\0\0\0\xff\xff\xff"  # a two-color table: black and white
    for frame in frames:
        width, height, left, top = (*frame, 0, 0)[:4]
        data += b"\x21\xf9\x04\x00\x05\x00\x00\x00"  # timing: 50 ms
        data += b"\x2c" + struct.pack("<HHHHB", left, top, width, height, 0)
        data += b"\x02\x02\x44\x01\x00"  # one pixel of compressed data
    return data + (b"\x3b" if trailer else b"")


def many_frames_gif(frames, size=4000):
    """A size × size GIF with `frames` frames that each change one pixel: a few
    bytes per frame in the file, but each is decoded at full size."""
    return hand_built_gif(size, [(1, 1)] * frames)
