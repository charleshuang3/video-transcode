import argparse
import os
import platform
import subprocess
from dataclasses import dataclass

import inquirer
from colorama import Fore, init
from pymediainfo import MediaInfo

init(autoreset=True)  # Initialize colorama

ALLOWED_TARGET_FILE_EXTENSIONS = [".mp4", ".mkv"]


# List tested pixel format here.
ALLOWED_COLORSPACES = ["YUV"]
ALLOWED_CHROMA_SUBSAMPLINGS = ["4:2:0"]
ALLOWED_BITDEPTHS = [8]

# List modern codecs here, if the original codec is modern, not much reason to change.
MODERN_VIDEO_CODECS = [
    "HEVC",  # H.265
    "AVC",  # H.264
]
MODERN_AUDIO_CODECS = ["AAC"]

# Default output video codec
DEFAULT_VIDEO_CODEC = "HEVC"
DEFAULT_AUDIO_CODEC = "AAC"

# audio bitrate in Xk
AUDIO_BITRATES = [96, 128, 192, 256, 320, 400]

CODEC_TO_ENDCODER = {
    "AVC": "h264_videotoolbox",
    "HEVC": "hevc_videotoolbox",
    "AAC": "aac",
}


@dataclass
class FFMPEGArgs:
    # -c:v HEVC -> h265_videotoolbox
    video_codec: str
    # -b:v 6M
    video_bitrate: int
    # -pix_fmt yuv420p
    video_pixel_format: str
    # audio copy
    audio_copy: bool
    # -c:a AAC -> aac
    audio_codec: str
    # -b:a 256k
    audio_bitrate: int

    def __str__(self):
        s = f"-c:v {CODEC_TO_ENDCODER[self.video_codec]} -b:v {int(self.video_bitrate)}M -pix_fmt {self.video_pixel_format}"
        if self.audio_copy:
            s += " -c:a copy"
        else:
            s += f" -c:a {CODEC_TO_ENDCODER[self.audio_codec]} -b:a {int(self.audio_bitrate)}k"
        return s


@dataclass
class Video:
    bitrate: int
    format: str
    width: int
    height: int
    frame_rate: float
    color_space: str
    chroma_subsampling: str
    bit_depth: int

    def normalize_bitrate(self) -> int:
        # video bitrate in M
        bitrate = self.bitrate / 1000 / 1000
        return bitrate + 1


@dataclass
class Audio:
    bitrate: int
    format: str

    def normalize_bitrate(self) -> int:
        # audio bitrate in k
        bitrate = self.bitrate / 1000
        for it in AUDIO_BITRATES:
            if it >= bitrate:
                return it

        print(
            f"❌ Audio bitrate {bitrate}k is too large, consider add to AUDIO_BITRATES"
        )
        exit(1)


@dataclass
class VideoMetadata:
    video: Video
    audio: Audio

    def __str__(self):
        return (
            f"Video Info:\n"
            f"  Audio Bitrate: {self.audio.bitrate}\n"
            f"  Audio Format: {self.audio.format}\n"
            f"  Video Bitrate: {self.video.bitrate}\n"
            f"  Video Format: {self.video.format}\n"
            f"  Width: {self.video.width}\n"
            f"  Height: {self.video.height}\n"
            f"  Frame Rate: {self.video.frame_rate}\n"
            f"  Color Space: {self.video.color_space}\n"
            f"  Chroma Subsampling: {self.video.chroma_subsampling}\n"
            f"  Bit Depth: {self.video.bit_depth}"
        )

    def to_ffmpeg_args(self) -> FFMPEGArgs:
        args = FFMPEGArgs(
            video_codec=DEFAULT_VIDEO_CODEC,
            video_bitrate=self.video.normalize_bitrate(),
            video_pixel_format="",
            audio_copy=False,
            audio_codec=DEFAULT_AUDIO_CODEC,
            audio_bitrate=self.audio.normalize_bitrate(),
        )

        if self.video.color_space == "YUV":
            args.video_pixel_format = "yuv"
        if self.video.chroma_subsampling == "4:2:0":
            args.video_pixel_format += "420"
        if self.video.bit_depth == 8:
            args.video_pixel_format += "p"

        if self.audio.format in MODERN_AUDIO_CODECS:
            args.audio_copy = True

        return args


def get_media_info(file_path) -> VideoMetadata:
    media_info = MediaInfo.parse(file_path)

    audio_tracks = media_info.audio_tracks

    if len(audio_tracks) != 1:
        print("❌ Expected exactly one audio track")
        exit(1)

    audio_track = audio_tracks[0]
    if audio_track.channel_s != 2:
        print("❌ Expected stereo audio track")
        exit(1)

    video_tracks = media_info.video_tracks
    if len(video_tracks) != 1:
        print("❌ Expected exactly one video track")
        exit(1)

    video_track = video_tracks[0]

    if video_track.color_space not in ALLOWED_COLORSPACES:
        print(f"❌ Expected color space to be one of {ALLOWED_COLORSPACES}")
        exit(1)
    if video_track.chroma_subsampling not in ALLOWED_CHROMA_SUBSAMPLINGS:
        print(f"Expected chroma subsampling to be one of {ALLOWED_CHROMA_SUBSAMPLINGS}")
        exit(1)
    if video_track.bit_depth not in ALLOWED_BITDEPTHS:
        print(f"❌ Expected bit depth to be one of {ALLOWED_BITDEPTHS}")
        exit(1)

    return VideoMetadata(
        audio=Audio(
            bitrate=int(audio_track.bit_rate),
            format=audio_track.format,
        ),
        video=Video(
            bitrate=int(video_track.bit_rate),
            format=video_track.format,
            width=int(video_track.width),
            height=int(video_track.height),
            frame_rate=float(video_track.frame_rate),
            color_space=video_track.color_space,
            chroma_subsampling=video_track.chroma_subsampling,
            bit_depth=int(video_track.bit_depth),
        ),
    )


def create_transcode_directory():
    home_dir = os.path.expanduser("~")
    tmp_transcode_dir = os.path.join(home_dir, "tmp", "transcode")
    tmp_dir = "/tmp/transcode"

    if os.path.exists(os.path.join(home_dir, "tmp")):
        if not os.path.exists(tmp_transcode_dir):
            os.makedirs(tmp_transcode_dir)

        return tmp_transcode_dir
    else:
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

        return tmp_dir


def is_m_chip_mac():
    """Checks if the current machine is an Apple Silicon (M-chip) Mac."""
    return platform.system() == "Darwin" and platform.machine() in ("arm64", "aarch64")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcode video files.")
    parser.add_argument(
        "-it", "--interactive", action="store_true", help="Enable interactive mode"
    )
    parser.add_argument("-i", "--input", help="Input file path", required=True)
    parser.add_argument("target", help="Target file path")

    args = parser.parse_args()

    transcode_dir = create_transcode_directory()

    print(Fore.LIGHTGREEN_EX + "====== Step 0: Check it is running on M-Chip Mac ===")
    if is_m_chip_mac():
        print("✅ Running on M-Chip Mac")
    else:
        print("❌ Running on non-M-Chip Mac")
        exit(1)

    print(Fore.LIGHTGREEN_EX + "====== Step 1: Check if input file exists ==========")
    input_file = args.input

    if not os.path.exists(input_file):
        print(f"❌ Input file {input_file} does not exist.")
        exit(1)
    print("✅ Input file exists")

    print(Fore.LIGHTGREEN_EX + "====== Step 2: Check if target file ================")
    target_file = args.target

    # Check if the target file directory exists
    target_file_dir = os.path.dirname(target_file)
    if not os.path.exists(target_file_dir):
        print(f"❌ Target file directory {target_file_dir} does not exist.")
        exit(1)

    print("✅ Target file directory exists")

    # Check if target file extension is in the allowed list
    target_file_ext = os.path.splitext(target_file)[1]
    if target_file_ext not in ALLOWED_TARGET_FILE_EXTENSIONS:
        print(
            f"❌ Target file extension {target_file_ext} is not allowed. Allowed extensions are {ALLOWED_TARGET_FILE_EXTENSIONS}"
        )
        exit(1)

    print("✅ Target file extension allowed")

    print(Fore.LIGHTGREEN_EX + "====== Step 3: Copy input file to tmp dir ==========")
    if not input_file.startswith(transcode_dir):
        # Use rsync to copy the file
        command = f"rsync -av --progress '{input_file}' '{transcode_dir}'"
        try:
            subprocess.run(
                command, shell=True, check=True, capture_output=False, text=True
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to copy {input_file} to {transcode_dir}. {e}")
            exit(1)

        input_file = os.path.join(transcode_dir, os.path.basename(input_file))

    print("✅ Input file copied to tmp dir")

    print(Fore.LIGHTGREEN_EX + "====== Step 4: Check media info of input file ======")

    video_metadata = None
    try:
        video_metadata = get_media_info(input_file)
        print(f"{video_metadata}")

    except Exception as e:
        print(f"❌ Could not retrieve media info for {input_file}. {e}")
        exit(1)

    interactive = args.interactive
    if not interactive:
        if (
            video_metadata.video.format in MODERN_VIDEO_CODECS
            and video_metadata.audio.format in MODERN_AUDIO_CODECS
        ):
            print(
                f"❌ video codec and audio codec already in modern codec, no reason to convert in script mode"
            )
            exit(0)

    print(Fore.LIGHTGREEN_EX + "====== Step 5: Prepare ffmpeg command ==============")
    ffmpeg_args = video_metadata.to_ffmpeg_args()

    if interactive:
        questions = [
            inquirer.List(
                "video_codec",
                message=f"Video Codec: {video_metadata.video.format} ->",
                choices=MODERN_VIDEO_CODECS,
            ),
            inquirer.Text(
                "video_bitrate",
                message=f"Video Bitrate: {video_metadata.video.bitrate / 1000}k -> M",
                default=str(int(ffmpeg_args.video_bitrate)),
            ),
            inquirer.Text(
                "video_pixel_format",
                message=f"Video Pixel Format (leave it empty to not change): {ffmpeg_args.video_pixel_format} ->",
            ),
            inquirer.Confirm(
                "audio_copy",
                message=f"Copy original audio track [{video_metadata.audio.format} {video_metadata.audio.bitrate / 1000}k]",
                default=ffmpeg_args.audio_copy,
            ),
        ]

        answers = inquirer.prompt(questions)
        ffmpeg_args.video_codec = answers["video_codec"]
        ffmpeg_args.video_bitrate = int(answers["video_bitrate"])

        if answers["video_pixel_format"]:
            ffmpeg_args.video_pixel_format = answers["video_pixel_format"]

        ffmpeg_args.audio_copy = answers["audio_copy"]

        if not ffmpeg_args.audio_copy:
            questions = [
                inquirer.List(
                    "audio_codec",
                    message=f"Audio Codec: {video_metadata.video.format} ->",
                    choices=MODERN_AUDIO_CODECS,
                ),
                inquirer.Text(
                    "audio_bitrate",
                    message=f"Audio Bitrate: {video_metadata.audio.bitrate / 1000}k -> k",
                    default=str(int(ffmpeg_args.audio_bitrate)),
                ),
            ]
            answers = inquirer.prompt(questions)
            ffmpeg_args.audio_codec = answers["audio_codec"]
            ffmpeg_args.audio_bitrate = int(answers["audio_bitrate"])

    print(f"{ffmpeg_args}")

    if interactive:
        questions = [inquirer.Confirm("continue", message="Looks Good?")]
        answers = inquirer.prompt(questions)
        if not answers["continue"]:
            exit(0)

    print(Fore.LIGHTGREEN_EX + "====== Step 6: start ffmpeg transcode ==============")
    temp_target_file = os.path.join(
        transcode_dir, "transcoded-" + os.path.basename(target_file)
    )

    ffmpeg_cmd = f"ffmpeg -i '{input_file}' {ffmpeg_args} '{temp_target_file}'"
    try:
        subprocess.run(
            ffmpeg_cmd, shell=True, check=True, capture_output=False, text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to transcode. {e}")
        exit(1)

    print("✅ Transcoded")

    print(Fore.LIGHTGREEN_EX + "====== Step 7: copy transcoded file to target ======")
    try:
        # Use rsync to copy the file
        command = f"rsync -av --progress '{temp_target_file}' '{target_file}'"
        subprocess.run(command, shell=True, check=True, capture_output=False, text=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to copy {temp_target_file} to {target_file}. {e}")
        exit(1)

    print("✅ Transcoded file copied to target")
