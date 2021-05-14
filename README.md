# Picture Book

Turn a video into a picture book of subtitled screenshots.

## Install

Ensure that you have Python 3.7+ (tested on 3.9) and [FFmpeg](https://ffmpeg.org/) (the `ffmpeg` and `ffprobe` binaries must be in your `PATH`, and FFmpeg must be configured with `--enable-libass`).

Install the `srt` library with `pip install srt` or from `requirements.txt`.

This script only produces screenshots, so you will need another tool to turn the screenshots into a PDF or ebook. For example, [ImageMagick](http://www.imagemagick.org/) can convert images to PDFs.

## Usage

You will need a video and subtitles. If the subtitles are included in the video, you can run:

```
python picture-book.py video output-dir
```

If the subtitles are in a separate file, you can use the `--subs` option:

```
python picture-book.py --subs subtitles.srt video output-dir
```

By default, the screenshots are color JPGs, scaled down to a width of 640px. Extra screenshots are added to ensure that the gap between two screenshots is never more than 5 seconds. To change these settings, see [Options](#options).

To create a book out of the screenshots, you will need a separate tool. For example, you can use ImageMagick to create a PDF:

```
convert output-dir/*.jpg book.pdf
```

Or, you can create a [CBZ](https://en.wikipedia.org/wiki/Comic_book_archive) by zipping the screenshots:

```
zip book.cbz output-dir/*.jpg
```

Other formats, such as EPUBs, will require different tools.

## Notes

This script will probably break if your video isn't "normal" (e.g. if the container has multiple video or subtitle streams, if the frame rate isn't constant, etc). Sorry about that. Media files can be complicated and it's hard to handle every possible case. But, it's hopefully not too hard to modify the script.

Also, the script works by generating a [`select`](https://ffmpeg.org/ffmpeg-filters.html#select_002c-aselect) filter that lists out every frame to screenshot. This command will be very long for long videos, so it may break. (I haven't tested it.) `select` also probably isn't as fast as a solution that directly seeks to every screenshot frame, but it allows everything to be done with one `ffmpeg` command.

Finally, the screenshot procedure works by taking one screenshot in the middle of each subtitle, along with screenshots of the first and last frames. Extra screenshots are uniformly spaced to ensure that the gap between two screenshots never exceeds a maximum number of seconds. This procedure is simple, but can miss scene changes, non-verbal sounds, etc. It could be interesting to improve this, but it's out of scope for this project.

## Options

* `--subs FILE`: Subtitle file to use instead of the video's default subtitle stream
* `--scale ARGS`: Arguments for the [`scale`](https://ffmpeg.org/ffmpeg-filters.html#scale-1) filter. The default is `640:-1`, which scales the screenshot width to 640px, while preserving the aspect ratio. Pass an empty string (i.e. `--scale ""`) to disable scaling.
* `--gray`: Convert screenshots to grayscale (default: screenshots are colored)
* `--max-gap SECONDS`: Maximum number of seconds between screenshots (default: 5 seconds)
* `--format {jpg,png}`: Screenshot image format. JPG (the default) is recommended to keep the file size low.
* `--jpg-quality QUALITY`: JPG image quality, from 2 (best, default) to 31 (worst).
* `--subtitle-style STYLE`: Custom subtitle style (formatted as ASS `KEY=VALUE` pairs separated by commas). It's probably best to use a subtitle editor to figure out what styles to use.

## Thanks

This project was inspired by [an anon on /tv/](https://archive.4plebs.org/tv/thread/127966847/#127967348).

## Legal

This program is licensed under the MIT License. See the `LICENSE` file for more information.
