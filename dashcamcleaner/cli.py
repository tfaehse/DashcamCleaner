#!/usr/bin/env python3

import argparse
import signal
from typing import Dict, Union

from src.blurrer import VideoBlurrer

# makes it possible to interrupt while running in other thread
signal.signal(signal.SIGINT, signal.SIG_DFL)


class CLI:
    def __init__(self, opt):
        self.opt = opt

    def start_blurring(self):
        # dump parameters
        print(vars(opt))

        # read inference size
        inference_size = int(self.opt.inference_size) * 16 / 9  # ouch again

        # set up parameters
        parameters: Dict[str, Union[bool, int, float, str]] = {
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

        # setup blurrer
        blurrer = VideoBlurrer(self.opt.weights, parameters)
        blurrer.blur_video()

        print("Video blurred successfully.")


def parse_arguments():
    class CustomHelpFormatter(argparse.HelpFormatter):
        def __init__(self, prog):
            super().__init__(prog, max_help_position=40, width=100)

        def _format_action_invocation(self, action):
            if not action.option_strings or action.nargs == 0:
                return super()._format_action_invocation(action)
            default = self._get_default_metavar_for_optional(action)
            args_string = self._format_args(action, default)
            return ", ".join(action.option_strings) + " " + args_string

    parser = argparse.ArgumentParser(
        formatter_class=CustomHelpFormatter,
        description=" This tool allows you to automatically censor faces and number plates on dashcam footage.",
    )

    required = parser.add_argument_group("required arguments")
    required.add_argument("-i", "--input", required=True, help="input video file path", type=str)
    required.add_argument(
        "-o",
        "--output",
        required=True,
        help="output video file path",
        type=str,
    )

    optional = parser.add_argument_group("optional arguments")
    optional.add_argument(
        "-w",
        "--weights",
        required=False,
        default="720p_medium_mosaic",
        help="Weights file to use. See readme for the differences",
        type=str,
    )
    optional.add_argument(
        "-s",
        "--batch_size",
        help="inference batch size - large values require a lof of memory and may cause crashes!",
        type=int,
        default=1,
        metavar="[1,1024]",
    )
    optional.add_argument(
        "-b",
        "--blur_size",
        required=False,
        help="granularity of the blurring filter",
        type=int,
        default=9,
        metavar="[1-99]",
    )
    optional.add_argument(
        "-if",
        "--inference_size",
        help="vertical inference size, e.g. 1080 or 720",
        type=int,
        default=720,
        metavar="[144-2160]",
    )
    optional.add_argument(
        "-t",
        "--threshold",
        required=False,
        help="detection threshold",
        type=float,
        default=0.4,
        metavar="[0-1]",
    )
    optional.add_argument(
        "-r",
        "--roi_multi",
        required=False,
        help="increase/decrease area that will be blurred - 1 means no change",
        type=float,
        default=1.0,
        metavar="[0-2]",
    )
    optional.add_argument(
        "-q",
        "--quality",
        metavar="[1, 10]",
        required=False,
        help="quality of the resulting video. higher = better, default: 10. conversion to crf: ⌊(1-q/10)*51⌋",
        type=float,
        choices=[round(x / 10, ndigits=2) for x in range(10, 101)],
        default=10,
    )
    optional.add_argument(
        "-f",
        "--frame_memory",
        required=False,
        help="blur objects in the last x frames too",
        type=int,
        metavar="[0-5]",
        choices=range(5 + 1),
        default=0,
    )
    optional.add_argument(
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
