"""
This script walks a given video directory checks each video for the following:

- Unwanted video/audio codecs: These might be fixable by transcoding.
- Low pixel resolution: Videos with a resolution of 720p or lower.
- Low bitrate:
    - 720p videos with a bitrate lower than 2500 kbps.
    - 1080p videos with a bitrate lower than 4000 kbps.
    - 4K videos with a bitrate lower than 7500 kbps.

Usage:
```
python check_video_dir.py -d /path/to/video/directory -o /path/to/report.csv
```
"""

import argparse
import csv
import mimetypes
import os
from dataclasses import dataclass

from pymediainfo import MediaInfo

mimetypes.add_type("video/x-matroska", ".mkv")
mimetypes.add_type("video/x-m4v", ".m4v")
mimetypes.add_type("video/x-ms-wmv", ".wmv")
mimetypes.add_type("video/mp2t", ".ts")


SUPPORTED_VIDEO_CODECS = [
    "HEVC",  # H.265
    "AVC",  # H.264
    "MPEG-4 Visual",  # MPEG-4
]
SUPPORTED_AUDIO_CODECS = [
    "FLAC",
    "PCM",
    "MPEG Audio",
    "AAC",
    "TRUEHD",  # Dolby TrueHD
    "AC3",  # Dolby Digit
    "AC-3",  # Dolby Digit
    "EAC3",  # Dolby Digit
    "E-AC-3",  # Dolby Digit
    "DTS",  # Dolby Digit
]

RESOLUTION_TO_MIN_BITRATE = {
    720: 2500,
    1080: 4000,
    2160: 7500,
}


@dataclass
class VideoCheckResult:
    file: str
    video_codec: str
    audio_codec: str
    resolution: int
    bitrate_k: int
    issues: list[str]

    def to_csv_row(self) -> list[str]:
        return [
            self.file,
            self.video_codec,
            self.audio_codec,
            str(self.resolution),
            str(self.bitrate_k),
            ", ".join(self.issues),
        ]


def is_video(video_path: str) -> bool:
    """Checks if a file is a video."""
    mime_type, _ = mimetypes.guess_type(video_path)
    return mime_type and mime_type.startswith("video/")


def check_video(video_path: str) -> VideoCheckResult:
    """Checks a video file and returns a VideoCheckResult object or None."""

    res = VideoCheckResult(
        file=video_path,
        video_codec="",
        audio_codec="",
        resolution=0,
        bitrate_k=0,
        issues=[],
    )

    media_info = MediaInfo.parse(video_path)
    if not media_info.video_tracks:
        res.issues.append("NO_VIDEO_TRACK")
        return res

    if not media_info.audio_tracks:
        res.issues.append("NO_AUDIO_TRACK")
        return res

    video_track = media_info.video_tracks[0]
    audio_track = media_info.audio_tracks[0]

    res.video_codec = video_track.format
    res.audio_codec = audio_track.format
    res.resolution = int(min(video_track.width, video_track.height))
    # Check video codec
    if res.video_codec not in SUPPORTED_VIDEO_CODECS:
        res.issues.append("VIDEO_CODEC")

    # Check audio codec
    if res.audio_codec not in SUPPORTED_AUDIO_CODECS:
        res.issues.append("AUDIO_CODEC")

    if res.resolution < 1080:
        res.issues.append("LOW_RESOLUTION")

    if video_track.bit_rate is None:
        res.issues.append("NO_BITRATE")
        return res

    res.bitrate_k = int(video_track.bit_rate / 1000)

    if not RESOLUTION_TO_MIN_BITRATE.get(res.resolution):
        res.issues.append("UNSUPPORTED_RESOLUTION")
        return res

    if RESOLUTION_TO_MIN_BITRATE.get(res.resolution) > res.bitrate_k:
        res.issues.append("LOW_BITRATE")

    return res


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-d", "--video_dir", help="Path to the video directory")
    parser.add_argument(
        "-o", "--output", help="Path to the output CSV report", default="report.csv"
    )
    args = parser.parse_args()

    if not os.path.isdir(args.video_dir):
        print(f"Error: {args.video_dir} is not a valid directory.")
        return

    results = []
    for root, _, files in os.walk(args.video_dir):
        for file in files:
            video_path = os.path.join(root, file)
            if not is_video(video_path):
                continue
            res = check_video(video_path)
            if len(res.issues) > 0:
                results.append(res)

    # Write to CSV
    file_existed = os.path.exists(args.output)
    with open(args.output, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_existed:
            writer.writerow(
                [
                    "File",
                    "Video Codec",
                    "Audio Codec",
                    "Resolution",
                    "Bitrate",
                    "Issues",
                ]
            )
        writer.writerows([res.to_csv_row() for res in results])


if __name__ == "__main__":
    main()
