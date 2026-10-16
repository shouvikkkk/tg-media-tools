# tg-media-tools

Watermark and compress images for Telegram sharing.

## Install

```bash
pip install -r requirements.txt
```

Requires Python 3 and Pillow.

## Usage

### watermark — overlay semi-transparent text on an image

```bash
python media_tools.py watermark input.jpg --text "@myhandle" --position bottom-right --opacity 128
```

Saves `input_watermarked.jpg`. Positions: `top-left`, `top-right`, `bottom-left`,
`bottom-right`, `center`. Opacity is 0 (invisible) to 255 (solid); default is 128.

### compress — shrink an image to fit under a size limit

```bash
python media_tools.py compress input.jpg --max-kb 500
```

Saves `input_compressed.jpg`. The tool lowers JPEG quality first, then downsizes the
image if needed, until the file fits under the limit.

### info — print image metadata

```bash
python media_tools.py info input.jpg
```

Prints dimensions, format, file size, and color mode. Example output:

```
Path:       input.jpg
Dimensions: 1200 x 800
Format:     JPEG
Mode:       RGB
File size:  234567 bytes (229.1 KB)
```

## License

MIT License — see [LICENSE](LICENSE).
