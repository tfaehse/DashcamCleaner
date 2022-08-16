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
            "feather_edges": self.opt.feather_edges,
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
    required.add_argument("-i", "--input", required=True, help="Input video file path.", type=str)
    required.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output video file path.",
        type=str,
    )

    optional = parser.add_argument_group("optional arguments")
    optional.add_argument(
        "-w",
        "--weights",
        required=False,
        help="Weights file to use. See readme for the differences. (default = 720p_medium_mosaic).",
        type=str,
        default="720p_medium_mosaic",
    )
    optional.add_argument(
        "-s",
        "--batch_size",
        help="Inference batch size - large values require a lof of memory and may cause crashes! Not recommended for CPU usage.",
        type=int,
        metavar="[1, 1024] = 1",
        default=1,
    )
    optional.add_argument(
        "-b",
        "--blur_size",
        required=False,
        help="Kernel radius of the gauss-filter.",
        type=int,
        metavar="[1, 99] = 9",
        default=9,
    )
    optional.add_argument(
        "-if",
        "--inference_size",
        help="Vertical inference size, e.g. 1080 or 720.",
        type=int,
        metavar="[144, 2160] = 720",
        default=720,
    )
    optional.add_argument(
        "-t",
        "--threshold",
        required=False,
        help="Detection threshold. Higher value means more certainty, lower value means more blurring.",
        type=float,
        metavar="[0.0, 1.0] = 0.4",
        default=0.4,
    )
    optional.add_argument(
        "-r",
        "--roi_multi",
        required=False,
        help="Increase/decrease area that will be blurred - 1.0 means no change.",
        type=float,
        metavar="[0.0, 2.0] = 1.0",
        default=1.0,
    )
    optional.add_argument(
        "-q",
        "--quality",
        required=False,
        help="Quality of the resulting video. higher = better. conversion to crf: ⌊(1-q/10)*51⌋.",
        type=float,
        choices=[round(x / 10, ndigits=2) for x in range(10, 101)],
        metavar="[1.0, 10.0] = 10.0",
        default=10,
    )
    optional.add_argument(
        "-f",
        "--frame_memory",
        required=False,
        help="Blur objects in the last x frames too.",
        type=int,
        metavar="[0, 5] = 0",
        choices=range(5 + 1),
        default=0,
    )
    optional.add_argument(
        "-fe",
        "--feather_edges",
        required=False,
        help="Feather edges of blurred areas, removes sharp edges on blur-mask. expands mask by argument and blurs mask, so effective size is twice the argument.",
        type=int,
        metavar="[0, 99] = 5",
        choices=range(99 + 1),
        default=5,
    )
    optional.add_argument(
        "-nf",
        "--no_faces",
        action="store_true",
        required=False,
        help="Fo not censor faces.",
        default=False,
    )
    return parser.parse_args()


if __name__ == "__main__":
    opt = parse_arguments()
    cli = CLI(opt)
    cli.start_blurring()
