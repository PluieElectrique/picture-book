import argparse
import math
import os
import subprocess
import sys
import tempfile

import srt


parser = argparse.ArgumentParser(
    description="Turn a video into a picture book by taking screenshots with subtitles."
)
parser.add_argument("video", help="Input video")
parser.add_argument("out_dir", help="Output directory for screenshots")
parser.add_argument(
    "--subs",
    help="Subtitle file (default: the video's subtitle stream will be used)",
)
parser.add_argument(
    "--scale",
    default="640:-1",
    help="Arguments for FFmpeg's scale filter (default: scale width to 640px, preserving aspect ratio). An empty string disables scaling.",
)
parser.add_argument(
    "--gray",
    action="store_true",
    help="Convert screenshots to grayscale (default: %(default)s)",
)
parser.add_argument(
    "--max-gap",
    type=float,
    default=5,
    help="Maximum number of seconds between screenshots (default: %(default)s)",
)
parser.add_argument(
    "--format",
    default="jpg",
    choices=["jpg", "png"],
    help="Screenshot format (default: %(default)s)",
)
parser.add_argument(
    "--jpg-quality",
    type=int,
    default=2,
    help="JPG quality, from 2 (best, default) to 31 (worst)",
)
parser.add_argument(
    "--subtitle-style",
    help="Custom subtitle style (format as ASS `KEY=VALUE` pairs separated by commas)",
)
args = parser.parse_args()


# Check arguments
if not (2 <= args.jpg_quality <= 31):
    print("jpq_quality must be between 2 and 31, inclusive")
    sys.exit()
elif args.max_gap <= 0:
    print("max_gap must be greater than 0")
    sys.exit()


def parse_ffprobe(entry):
    output = subprocess.run(
        [
            "ffprobe",
            # Suppress the banner and debug info
            "-v", "error",
            # Don't print the section tags or entry keys
            "-of", "default=noprint_wrappers=1:nokey=1",
            "-show_entries",
            entry,
            args.video,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return output.stdout.strip()


# Get duration (of container)
duration = float(parse_ffprobe("format=duration"))
# Get (average) FPS (first entry that is not "0/0")
for f in parse_ffprobe("stream=avg_frame_rate").split("\n"):
    if f != "0/0":
        frac = f.split("/")
        fps = float(frac[0]) / float(frac[1])
        break


print(f"Guessing that FPS is {fps} and duration is {duration} seconds.")


# filename can be a video or non-SubRip subtitle file
def convert_to_srt(filename):
    # Apparently, on Windows NT or later, the temporary file cannot be opened
    # by other processes while it's still open in Python. So, we have to close
    # it first.
    fd, temppath = tempfile.mkstemp(suffix=".srt")
    os.close(fd)
    try:
        # We need -y to ensure that the temporary file is overwritten
        subprocess.run(
            ["ffmpeg", "-y", "-i", filename, temppath],
            # Don't clutter the console
            capture_output=True,
            check=True,
        )
        with open(temppath) as f:
            return srt.parse(f.read())
    finally:
        os.remove(temppath)


# Get subtitles
if args.subs is None:
    print("Extracting subtitles from video... ", end="", flush=True)
    subtitles = convert_to_srt(args.video)
    print("Done.")
elif os.path.splitext(args.subs)[1] != ".srt":
    print("Converting subtitles to SRT... ", end="", flush=True)
    subtitles = convert_to_srt(args.subs)
    print("Done.")
else:
    with open(args.subs) as f:
        subtitles = srt.parse(f.read())


# Get subtitle timestamps. We also include the first and last frame.
timestamps = [0]
# We pick the middle of each subtitle so there's more room for error in case
# the calculated frame isn't accurate (e.g. due to rounding).
for sub_time in [(s.start + s.end).total_seconds() / 2 for s in subtitles] + [duration]:
    # Calculate screenshot times, adding evenly spaced screenshots if the gap
    # is too big.
    previous_timestamp = timestamps[-1]
    gap = sub_time - previous_timestamp
    screenshot_count = int(gap // args.max_gap) + 1
    timestamps.extend(
        previous_timestamp + gap * (i + 1) / screenshot_count
        for i in range(screenshot_count)
    )


# Construct video filter
vf = f"subtitles={args.subs or args.video}"
if args.subtitle_style:
    vf += f":force_style={args.subtitle_style}"
if args.scale:
    vf += f",scale='{args.scale}'"

# We pick frames to screenshot using a select filter. The select expression
# returns 0 for frames that should be ignored and -1 for frames that should be
# screenshotted. So, for frames f1, f2, ..., the expression looks like:
#
#   -eq(n, f1) - eq(n, f2) - ...
#
# where n is the current frame and eq(a, b) returns 1 if a == b and 0
# otherwise. This approach creates a long expression, which may be slow for
# long videos. But, it's simple, lets us do everything with one FFmpeg command,
# and seems to work fine if there are only a few hundred frames to screenshot.
# For more info, see:
#  - SO answer that inspired this: https://stackoverflow.com/a/47199740
#  - select filter: https://ffmpeg.org/ffmpeg-filters.html#select_002c-aselect
#  - Expression syntax: https://www.ffmpeg.org/ffmpeg-utils.html#Expression-Evaluation

vf += ",select='" + "".join(f"-eq(n,{int(t * fps)})" for t in timestamps) + "'"


# Format specific flags
if args.format == "png" and args.gray:
    # This ensures that grayscale PNGs are single-channel, which saves space.
    format_flags = ["-pix_fmt", "gray"]
elif args.format == "jpg":
    format_flags = ["-q:v", str(args.jpg_quality)]
    if args.gray:
        # FFmpeg doesn't seem to support single-channel JPGs, so pix_fmt won't
        # work. We use the format filter instead (it wastes space by using
        # three channels, but what can you do).
        vf += ",format=gray"
else:
    format_flags = []

# Filename pattern
digits_needed = int(math.log10(len(timestamps))) + 1
filename_pattern = f"%0{digits_needed}d.{args.format}"

os.makedirs(args.out_dir, exist_ok=True)

print(f"Extracting {len(timestamps)} screenshots.\n")

subprocess.run(
    [
        "ffmpeg",
        # Reduce clutter
        "-hide_banner",
        "-i", args.video,
        # I'm not sure exactly why this is needed, but without it, there are
        # tons of duplicate frames.
        "-vsync", "vfr",
        "-vf", vf,
        *format_flags,
        os.path.join(args.out_dir, filename_pattern),
    ]
)
