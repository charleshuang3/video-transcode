import unittest

from video_transcode import Audio, FFMPEGArgs, Video, VideoMetadata


class TestFFMPEGArgsStr(unittest.TestCase):
    def test_ffmpeg_args_str(self):
        # Test case 1: audio_copy = True
        args1 = FFMPEGArgs(
            video_codec="HEVC",
            video_bitrate=6,
            video_pixel_format="yuv420p",
            audio_copy=True,
            audio_codec="AAC",
            audio_bitrate=256,
        )
        expected_str1 = "-c:v hevc_videotoolbox -b:v 6M -pix_fmt yuv420p -c:a copy"
        self.assertEqual(str(args1), expected_str1)

        # Test case 2: audio_copy = False
        args2 = FFMPEGArgs(
            video_codec="AVC",
            video_bitrate=4,
            video_pixel_format="yuv420p",
            audio_copy=False,
            audio_codec="AAC",
            audio_bitrate=128,
        )
        expected_str2 = (
            "-c:v h264_videotoolbox -b:v 4M -pix_fmt yuv420p -c:a aac -b:a 128k"
        )
        self.assertEqual(str(args2), expected_str2)


class TestFFMPEGArgsToFFMPEGArgs(unittest.TestCase):
    def test_to_ffmpeg_args_modern_codecs(self):
        # Test case 1: Modern video and audio codecs, audio copy should be True
        video_metadata1 = VideoMetadata(
            video=Video(
                bitrate=2000000,
                format="HEVC",
                width=1920,
                height=1080,
                frame_rate=24.0,
                color_space="YUV",
                chroma_subsampling="4:2:0",
                bit_depth=8,
            ),
            audio=Audio(bitrate=128000, format="AAC"),
        )
        ffmpeg_args1 = video_metadata1.to_ffmpeg_args()
        expected_str1 = "-c:v hevc_videotoolbox -b:v 3M -pix_fmt yuv420p -c:a copy"
        self.assertEqual(str(ffmpeg_args1), expected_str1)

    def test_to_ffmpeg_args_non_modern_codecs(self):
        # Test case 2: Non-modern video and audio codecs, audio copy should be False
        video_metadata2 = VideoMetadata(
            video=Video(
                bitrate=2000000,
                format="AVC",
                width=1920,
                height=1080,
                frame_rate=24.0,
                color_space="YUV",
                chroma_subsampling="4:2:0",
                bit_depth=8,
            ),
            audio=Audio(bitrate=96000, format="MP3"),
        )
        ffmpeg_args2 = video_metadata2.to_ffmpeg_args()
        expected_str2 = (
            "-c:v hevc_videotoolbox -b:v 3M -pix_fmt yuv420p -c:a aac -b:a 96k"
        )
        self.assertEqual(str(ffmpeg_args2), expected_str2)

    def test_to_ffmpeg_args_normalize_bitrate(self):
        # Test case 3: Test bitrate normalization
        video_metadata3 = VideoMetadata(
            video=Video(
                bitrate=3000000,
                format="AVC",
                width=1920,
                height=1080,
                frame_rate=24.0,
                color_space="YUV",
                chroma_subsampling="4:2:0",
                bit_depth=8,
            ),
            audio=Audio(bitrate=192000, format="MP3"),
        )
        ffmpeg_args3 = video_metadata3.to_ffmpeg_args()
        expected_str3 = (
            "-c:v hevc_videotoolbox -b:v 4M -pix_fmt yuv420p -c:a aac -b:a 192k"
        )
        self.assertEqual(str(ffmpeg_args3), expected_str3)


if __name__ == "__main__":
    unittest.main()
