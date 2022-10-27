import json
import os.path
from PIL import Image, ImageSequence, ImageOps

ORIGINAL_SIZE = 512
TARGET_SIZE = 64
SEG_SIZE = ORIGINAL_SIZE // TARGET_SIZE
ALPHABET = r'''$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,"^`' '''

# MARKER is a temporary symbol which will by replaced with color id later
MARKER = '2'
assert len(MARKER) == 1 and MARKER not in ALPHABET

CSI = '\033['

CUR_POS = CSI + '{0};{1}H'
SET_FG_8 = CSI + f'38;5;{MARKER}m'


def number_to_ansi(n: int) -> str:
    assert 0 <= n < 1000
    return f'{n:03d}'


def map_to_ascii(v: float) -> str:
    a = ALPHABET
    v = v * len(a) / 255
    return a[len(a) - round(v) - 1]


def set_colors(frames: list[str]) -> None:
    # Load list of 8bit colors from file obtained from
    # https://www.ditig.com/256-colors-cheat-sheet
    with open('256-colors.json') as f:
        j = json.load(f)

        # Skip default 16 colors
        # Filter colors with saturation 100 and lightness 50
        colors = filter(lambda c: c['hsl']['s'] == 100 and c['hsl']['l'] == 50, j[16:])
        # Sort by hue
        colors = sorted(colors, key=lambda c: c['hsl']['h'], reverse=True)
        # Simplify to ids only
        colors = list(map(lambda c: c['colorId'], colors))

    step = 1 / len(frames)
    h = 1
    for i in range(len(frames)):
        # Set {0} to id of the closes color with leading zeroes
        s = number_to_ansi(colors[round(h * (len(colors) - 1))])
        frames[i] = frames[i].replace(MARKER, s, 1)
        h -= step


def bytes_to_str(data):
    indent = 2
    step = 16
    lines = (' ' * indent + ', '.join(map(lambda n: f'{n:#04x}', data[i:i+step])) for i in range(0, len(data), step))
    return '{\n' + ',\n'.join(lines) + '\n};'


def write_to_headers_file(frames: list[str]) -> None:
    frame_bytes = ''.join(frames).encode('ascii')
    with open(os.path.join('..', 'cat.h'), 'w') as f:
        f.write(f'unsigned int frame_len = {len(frame_bytes) // len(frames)};\n')
        f.write(f'unsigned int frame_count = {len(frames)};\n')
        f.write(f'unsigned int frame_w = {TARGET_SIZE * 2};\n')
        f.write(f'unsigned int frame_h = {TARGET_SIZE};\n')
        f.write('unsigned char frames[] = ')
        f.write(bytes_to_str(frame_bytes))


def main():
    ascii_frames = []
    img = Image.open('cat.gif')
    for frame in ImageSequence.Iterator(img):
        pixels = ImageOps.grayscale(frame).load()
        segments = []
        for seg_y in range(TARGET_SIZE):
            # CUR_POS sequence is 1-based
            segments.append(CUR_POS.format(number_to_ansi(seg_y + 1), number_to_ansi(1)))

            for seg_x in range(TARGET_SIZE * 2):
                value = 0
                for y in range(SEG_SIZE):
                    for x in range(SEG_SIZE // 2):
                        value += pixels[SEG_SIZE // 2 * seg_x + x, SEG_SIZE * seg_y + y]
                value /= SEG_SIZE ** 2
                segments.append(map_to_ascii(value))

        fr = SET_FG_8 + ''.join(segments)
        ascii_frames.append(fr)

    set_colors(ascii_frames)
    write_to_headers_file(ascii_frames)


if __name__ == '__main__':
    main()
