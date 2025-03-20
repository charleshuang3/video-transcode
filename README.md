# Video Transcode

This project is a Python script that transcodes video files from older, less streaming-friendly
codecs to modern codecs like H.265 (HEVC) and H.264 (AAC). It's designed to be used on M-Chip Macs
and leverages the VideoToolbox framework for hardware-accelerated transcoding.

## Prerequisites

*   An M-Chip Mac (Apple Silicon)
*   Python 3.13+
*   FFmpeg
*   Rsync


## Installation

1.  Clone the repository:

    ```bash
    git clone <repository_url>
    cd video-transcode
    ```

2.  Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

```bash
python video_transcode.py -i <input_file> <target_file>
```

*   `<input_file>`: The path to the input video file.
*   `<target_file>`: The path to the output video file.

### Example

```bash
python video_transcode.py -i input.avi output.mp4
```

This command will transcode `input.avi` to `output.mp4` using the default settings.

### Interactive Mode

You can run the script in interactive mode to customize the transcoding settings:

```bash
python video_transcode.py -it -i input.avi output.mp4
```

This will prompt you with a series of questions to configure the video and audio codecs, bitrates, and other options.

## Limitation

*   The script currently only supports single audio and video tracks.
*   The script expects the audio track to be stereo.
*   The script only supports YUV color space, 4:2:0 chroma subsampling, and 8-bit depth.
*   The script copies the input file to a temporary directory before transcoding.
*   The script uses `rsync` to copy files.
