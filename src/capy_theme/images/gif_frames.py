"""Reading a GIF's frame sizes from its structure, without decoding any pixels.

A GIF's first block says how big the image is, but each frame has its own
position and size, and a frame can reach past that. Pillow then makes the whole
image bigger when it decodes the frames (after any check of the first size), or
fails. So the upload checks use frame_extent(), which reads every frame's header
and skips the compressed pixel data (issue #188).

It's stricter than Pillow on purpose: bytes Pillow would skip between blocks, a
frame with no pixels, or a file that ends inside a block are all BrokenGif.
"""

import struct

# The GIF layout (GIF89a spec): a 13-byte header and screen descriptor (the image's
# size at offset 6, its flags at 10), an optional color table, then blocks.
HEADER_SIZE = 13
SIZE_OFFSET = 6
# Each block starts with one of these bytes.
TRAILER = 0x3B  # the end of the file
EXTENSION = 0x21  # comments, timing, looping...: a label, then data sub-blocks
IMAGE = 0x2C  # a frame: a 10-byte descriptor (this byte, left, top, width,
# height, flags), an optional color table, the LZW code size byte, data sub-blocks
DESCRIPTOR_SIZE = 10
# In the flags byte: whether a color table follows, and its size (2^(n+1) colors).
HAS_COLOR_TABLE = 0x80
COLOR_TABLE_BITS = 0x07


class BrokenGif(ValueError):
    """The file doesn't follow the GIF structure."""


def _color_table_size(flags):
    """Bytes in the color table these flags describe (3 per color)."""
    if not flags & HAS_COLOR_TABLE:
        return 0
    return 3 * 2 ** ((flags & COLOR_TABLE_BITS) + 1)


def _skip_sub_blocks(data, pos):
    """The position after a run of data sub-blocks (each starts with its length;
    a zero length ends the run)."""
    while data[pos]:
        pos += data[pos] + 1
    return pos + 1


def frame_extent(data):
    """(frames, width, height): the number of frames and the size the image
    reaches once every frame is placed. Raises BrokenGif for a damaged file."""
    try:
        width, height, flags = struct.unpack_from("<HHB", data, SIZE_OFFSET)
        pos = HEADER_SIZE + _color_table_size(flags)
        frames = 0
        # Some GIFs leave out the trailer; ending between blocks is fine.
        while pos < len(data) and data[pos] != TRAILER:
            if data[pos] == EXTENSION:
                pos = _skip_sub_blocks(data, pos + 2)  # after the label
            elif data[pos] == IMAGE:
                left, top, frame_width, frame_height, local = struct.unpack_from(
                    "<HHHHB", data, pos + 1
                )
                if not frame_width or not frame_height:
                    raise BrokenGif(f"Frame {frames + 1} has no pixels.")
                frames += 1
                width = max(width, left + frame_width)
                height = max(height, top + frame_height)
                pos += DESCRIPTOR_SIZE + _color_table_size(local)
                pos = _skip_sub_blocks(data, pos + 1)  # after the LZW code size
            else:
                raise BrokenGif(f"Unexpected byte {data[pos]:#x} at {pos}.")
    except (IndexError, struct.error) as error:
        raise BrokenGif("The file ends in the middle of a block.") from error
    return frames, width, height
