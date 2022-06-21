#!/usr/bin/env python3

from argparse import ArgumentParser

from src.blurrer import VideoBlurrer


class CLI():

    def __init__(self, opt):
        """
        Constructor
        """
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
            "quality": self.opt.quality
        }
        if self.blurrer:
            self.blurrer.parameters = parameters
            self.blurrer.start()
        else:
            print("No blurrer object!")
        print("Blurrer started!")
        self.blurrer.wait()
        if self.blurrer and self.blurrer.result["success"]:
            minutes = int(self.blurrer.result["elapsed_time"] // 60)
            seconds = round(self.blurrer.result["elapsed_time"] % 60)
            print(f"Video blurred successfully in {minutes} minutes and {seconds} seconds.")
        else:
            print("Blurring resulted in errors.")


def parse_arguments():
    parser = ArgumentParser()
    parser.add_argument("input", help="input video file path", type=str)
    parser.add_argument("output", help="output video file path", type=str)
    parser.add_argument("weights", help="weights file name", type=str)
    parser.add_argument("inference_size", help="vertical inference size, e.g. 1080 or fHD", type=int)
    parser.add_argument("threshold", help="detection threshold", type=float)
    parser.add_argument("blur_size", help="granularity of the blurring filter", type=int)
    parser.add_argument("frame_memory", help="blur objects in the last x frames too", type=int)
    parser.add_argument("roi_multi", help="increase/decrease area that will be blurred - 1 means no change", type=float)
    parser.add_argument("quality", help="quality of the resulting video", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    opt = parse_arguments()
    cli = CLI(opt)
    cli.start_blurring()
