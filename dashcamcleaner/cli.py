#!/usr/bin/env python3

import argparse
import signal
import sys
import textwrap
from pathlib import Path
from typing import Dict, List, Union
import re

from src.blurrer import VideoBlurrer

# makes it possible to interrupt while running in other thread
signal.signal(signal.SIGINT, signal.SIG_DFL)


class CLI:
    def __init__(self, opt) -> None:
        """
        Class for blurring videos from a CLI
        :param opt: set of input arguments
        """
        self.opt = opt
        self.sanitize_opts()

    def sanitize_opts(self):
        """
        Sanity check for paths in input arguments
        """
        input_path, output_path = Path(self.opt.input_path), Path(self.opt.output_path)
        if input_path.is_file() and output_path.is_dir():  # if input refers a file, output must refer to a file too
            self.opt.output_path = (output_path / input_path.name).absolute()
            output_path = Path(self.opt.output_path)
        if output_path.is_file():
            sys.exit(f'The output_path "{self.opt.output_path}" already exists. The file will not be overwritten.')
        if input_path.is_dir():  # batch processing mode
            if not output_path.is_dir():
                sys.exit("For batch processing mode, both input_path and output_path must be directories!")
            if not any(input_path.glob("*.*")):
                sys.exit("The input_path is empty. Nothing to do.")
            for input_file in input_path.glob("*.*"):
                test_out_path = output_path / input_file.name
                if test_out_path.exists():
                    sys.exit(f'The output_path "{test_out_path.absolute()}" already exists. Aborting.')
        elif not input_path.is_file():
            sys.exit("input_path is invalid")

    def start_blurring(self):
        """
        Start the blurring process(es)
        """
        input_path, output_path = Path(self.opt.input_path), Path(self.opt.output_path)
        if input_path.is_dir():  # batch mode
            for input_file in sorted(input_path.glob("*.*")):
                self.opt.input_path = input_file.absolute()
                self.opt.output_path = (output_path / input_file.name).absolute()
                self.start_blurring_file()
        else:
            self.start_blurring_file()

    def start_blurring_file(self):
        """
        Blur a single video file
        """
        print("Start blurring video:", self.opt.input_path)
        print("Blurring parameter:", vars(self.opt))

        # set up parameters
        parameters: Dict[str, Union[bool, int, float, str]] = vars(self.opt)  # convert opt to dict type

        # read inference size
        model_name: str = parameters["weights"]
        training_inference_size: int = int(re.search(r"(?P<imgsz>\d*)p\_", model_name).group("imgsz"))
        parameters["inference_size"] = int(training_inference_size * 16 / 9)

        # setup blurrer
        blurrer = VideoBlurrer(self.opt.weights, parameters)
        blurrer.blur_video()

        print("Blurred video successfully written to:", self.opt.output_path)


def parse_arguments():
    """
    Argument parser
    :return: set of parsed arguments
    """

    class CustomHelpFormatter(argparse.HelpFormatter):
        def __init__(self: "CustomHelpFormatter", prog) -> None:
            super().__init__(prog, max_help_position=8)
            # import re
            # self._whitespace_matcher = re.compile(r'[.]+', re.ASCII)

        def _format_action_invocation(self: "CustomHelpFormatter", action):
            if not action.option_strings:
                return "  " + super()._format_action_invocation(action)
            default = self._get_default_metavar_for_optional(action)
            args_string = self._format_args(action, default)
            default_value = ""
            if action.default is not None and action.default is not argparse.SUPPRESS:
                default_value = f"  (Default: {action.default})"
            return f"  {action.option_strings[0]} {args_string}{default_value}\n    {action.option_strings[1]} {args_string}"

        def _split_lines(self: "CustomHelpFormatter", text: str, width: int) -> List[str]:
            ret = []
            for line in text.splitlines():
                if len(line) > width:
                    ret.extend(textwrap.wrap(line, width, replace_whitespace=False, break_long_words=False))
                else:
                    ret.extend([line])

            # add empty line to separate each argument
            if len(ret[-1]) > 0:
                ret.extend([""])

            return ret

    parser = argparse.ArgumentParser(
        formatter_class=CustomHelpFormatter,
        description="This tool allows you to automatically censor faces and number plates on dashcam footage.",
        add_help=False,  # for custom grouping, at the end after required args
    )

    required = parser.add_argument_group("required arguments")
    required.add_argument(
        "-i",
        "--input_path",
        required=True,
        help="Input video file path. Pass a folder name for batch processing all files in the folder.",
        type=str,
    )
    required.add_argument(
        "-o",
        "--output_path",
        required=True,
        help="Output video file path. Pass a folder name for batch processing.",
        type=str,
    )

    optional = parser.add_argument_group("optional arguments")
    advanced = parser.add_argument_group("optional arguments (advanced)")

    optional.add_argument(
        "-w",
        "--weights",
        required=False,
        help="Weights file to use. See readme for the differences. (default = 720p_medium_mosaic).",
        type=str,
        default="720p_medium_mosaic",
    )
    optional.add_argument(
        "-bw",
        "--blur_workers",
        required=False,
        help="Amount of processes to use for blurring frames. (default = 2)",
        type=int,
        default=2,
    )
    advanced.add_argument(
        "-s",
        "--batch_size",
        help="""Inference batch size - large values require a lof of memory and may cause crashes!
This will read multiple frames at the same time and perform detection on all of those at once.
Not recommended for CPU usage.""",
        type=int,
        metavar="[1, 1024]",
        default=2,
    )
    optional.add_argument(
        "-b",
        "--blur_size",
        required=False,
        help="Kernel radius of the blurring-filter. Higher value means more blurring, 0 would mean no blurring at all.",
        type=int,
        metavar="[1, 99]",
        default=9,
    )
    optional.add_argument(
        "-t",
        "--threshold",
        required=False,
        help="Detection threshold. Higher value means more certainty, lower value means more blurring. This setting affects runtime, a lower threshold means slower execution times.",
        type=float,
        metavar="[0.0, 1.0]",
        default=0.4,
    )
    optional.add_argument(
        "-r",
        "--roi_multi",
        required=False,
        help="Increase or decrease the area that will be blurred - 1.0 means no change.",
        type=float,
        metavar="[0.0, 2.0]",
        default=1.0,
    )
    optional.add_argument(
        "-q",
        "--quality",
        required=False,
        help="""Quality of the resulting video. higher = better. Conversion to crf: ⌊(1-q/10)*51⌋.""",
        type=float,
        choices=[round(x / 10, ndigits=2) for x in range(10, 101)],
        metavar="[1.0, 10.0]",
        default=10,
    )
    optional.add_argument(
        "-fe",
        "--feather_edges",
        required=False,
        help="Feather edges of blurred areas, removes sharp edges on blur-mask. \nExpands mask by argument and blurs mask, so effective size is twice the argument.",
        type=int,
        metavar="[0, 99]",
        choices=range(99 + 1),
        default=5,
    )
    optional.add_argument(
        "-nf",
        "--no_faces",
        action="store_true",
        required=False,
        help="Do not censor faces.",
        default=False,
    )
    optional.add_argument(
        "-bm",
        "--blur_memory",
        required=False,
        help="Blur detected plates from n previous frames too in order to (maybe) cover up missed identifiable information",
        type=int,
        metavar="[0, 10]",
        choices=range(10 + 1),
        default=0
    )
    advanced.add_argument(
        "-m",
        "--export_mask",
        action="store_true",
        required=False,
        help="Export a black and white only video of the blur-mask without applying it to the input clip.",
        default=False,
    )
    advanced.add_argument(
        "-mc",
        "--export_colored_mask",
        action="store_true",
        required=False,
        help="""Export a colored mask video of the blur-mask without applying it to the input clip.
The value represents the confidence of the detector.
Lower values mean less confidence, brighter colors mean more confidence.
If the --threshold setting is larger than 0 then detections with a lower confidence are discarded.
Channels; Red: Faces, Green: Numberplates.
Hint: turn off --feather_edges by setting -fe=0 and turn --quality to 10""",
        default=False,
    )
    advanced.add_argument(
        "-j",
        "--export_json",
        action="store_true",
        required=False,
        help="Export detections (based on index) to a JSON file.",
        default=False,
    )
    optional.add_argument(
        "-h", "--help", action="help", default=argparse.SUPPRESS, help="Show this help message and exit."
    )

    return parser.parse_args()


if __name__ == "__main__":
    opt = parse_arguments()
    cli = CLI(opt)
    cli.start_blurring()
