"""Reading a GIF's frame sizes from its structure, without decoding any pixels.

A GIF's first block says how big the image is, but each frame has its own
position and size, and a frame can reach past that. Pillow then makes the whole
image bigger when it decodes the frames, which is after any check of the first
size. So the upload checks use frame_extent(), which reads every frame's header
(and skips the compressed pixel data) to find the size the image really reaches
(issue #188).
"""

import struct

TRAILER = 0x3B
EXTENSION = 0x21
IMAGE = 0x2C


class BrokenGif(ValueError):
    """The file doesn't follow the GIF structure."""


def _color_table_size(flags):
    return 3 * 2 ** ((flags & 7) + 1) if flags & 0x80 else 0


def _skip_sub_blocks(data, pos):
    """The position after a run of data sub-blocks (each starts with its length)."""
    while data[pos]:
        pos += data[pos] + 1
    return pos + 1


def frame_extent(data):
    """(frames, width, height): the number of frames and the size the image
    reaches once every frame is placed. Raises BrokenGif for a damaged file."""
    try:
        width, height, flags = struct.unpack_from("<HHB", data, 6)
        pos = 13 + _color_table_size(flags)
        frames = 0
        # Some GIFs leave out the trailer; ending between blocks is fine.
        while pos < len(data) and data[pos] != TRAILER:
            if data[pos] == EXTENSION:
                pos = _skip_sub_blocks(data, pos + 2)
            elif data[pos] == IMAGE:
                left, top, frame_width, frame_height, local = struct.unpack_from(
                    "<HHHHB", data, pos + 1
                )
                frames += 1
                width = max(width, left + frame_width)
                height = max(height, top + frame_height)
                pos += 10 + _color_table_size(local)
                pos = _skip_sub_blocks(data, pos + 1)  # after the LZW code size
            else:
                raise BrokenGif(f"Unexpected byte {data[pos]:#x} at {pos}.")
    except (IndexError, struct.error) as error:
        raise BrokenGif("The file ends in the middle of a block.") from error
    return frames, width, height
