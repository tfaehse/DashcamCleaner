#!/usr/bin/env python3

import signal
from argparse import ArgumentParser

from src.blurrer import VideoBlurrer

# makes it possible to interrupt while running in other thread
signal.signal(signal.SIGINT, signal.SIG_DFL)


class CLI:
    def __init__(self, opt):
        self.opt = opt
        self.blurrer = None

    def start_blurring(self):
        # setup blurrer
        self.blurrer = VideoBlurrer(self.opt.weights)

        # read inference size
        inference_size = int(self.opt.inference_size) * 16 / 9  # ouch again

        # set up parameters
        parameters = {
            "input_path": self.opt.input,
            "output_path": self.opt.output,
            "blur_size": self.opt.blur_size,
            "blur_memory": self.opt.frame_memory,
            "threshold": self.opt.threshold,
            "roi_multi": self.opt.roi_multi,
            "inference_size": inference_size,
            "quality": self.opt.quality,
            "batch_size": self.opt.batch_size,
            "no_faces": self.opt.no_faces,
        }
        if self.blurrer:
            self.blurrer.parameters = parameters
            self.blurrer.blur_video()
        else:
            print("No blurrer object!")
        print("Video blurred successfully.")


def parse_arguments():
    parser = ArgumentParser(
        description=" This tool allows you to automatically censor faces and number plates on dashcam footage."
    )

    required_named = parser.add_argument_group("required named arguments")

    required_named.add_argument(
        "-i", "--input", metavar="INPUT_PATH", required=True, help="input video file path", type=str
    )
    required_named.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT_NAME",
        required=True,
        help="output video file path",
        type=str,
    )
    required_named.add_argument(
        "-w", "--weights", metavar="WEIGHTS_FILE_NAME", required=True, help="", type=str
    )
    required_named.add_argument(
        "--threshold", required=True, help="detection threshold", type=float
    )
    required_named.add_argument(
        "--blur_size", required=True, help="granularity of the blurring filter", type=int
    )
    required_named.add_argument(
        "--frame_memory", required=True, help="blur objects in the last x frames too", type=int
    )

    parser.add_argument(
        "--batch_size",
        help="inference batch size - large values require a lof of memory",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--inference_size", help="vertical inference size, e.g. 1080 or fHD", type=int, default=1080
    )
    parser.add_argument(
        "--roi_multi",
        required=False,
        help="increase/decrease area that will be blurred - 1 means no change",
        type=float,
        default=1.0,
    )
    parser.add_argument(
        "-q",
        "--quality",
        metavar="[1, 10]",
        required=False,
        help="quality of the resulting video. in range [1, 10] from 1 - bad to 10 - best, default: 10",
        type=int,
        choices=range(1, 11),
        default=10,
    )
    parser.add_argument(
        "-nf",
        "--no_faces",
        action="store_true",
        required=False,
        help="do not censor faces",
        default=False,
    )
    return parser.parse_args()


if __name__ == "__main__":
    opt = parse_arguments()
    cli = CLI(opt)
    cli.start_blurring()
