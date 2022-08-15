import os
import subprocess
from math import sqrt
from shutil import which
from typing import Dict, List, Union

import cv2
import imageio
import numpy as np
import torch
from more_itertools import chunked
from src.bounds import Bounds
from src.detection import Detection
from tqdm import tqdm


class VideoBlurrer:
    parameters: Dict[str, Union[bool, int, float, str]]
    detections: List[Detection]

    def __init__(self: 'VideoBlurrer', weights_name: str, parameters: Dict[str, Union[bool, int, float, str]]) -> None:
        """
        Constructor
        :param weights_name: file name of the weights to be used
        :param parameters: all relevant paremeters for the blurring process
        """
        self.parameters = parameters
        self.detections = []
        weights_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "weights",
            f"{weights_name}.pt".replace(".pt.pt", ".pt"),
        )
        self.detector = setup_detector(weights_path)
        print("Worker created")

    def apply_blur(self: 'VideoBlurrer', frame: np.array, new_detections: List[Detection]):
        """
        Apply Gaussian blur to regions of interests
        :param frame: input image
        :param new_detections: list of newly detected faces and plates
        :return: processed image
        """
        # gather inputs from self.parameters
        blur_size = self.parameters["blur_size"] * 2 + 1  # must be odd
        blur_memory = self.parameters["blur_memory"]
        roi_multi = self.parameters["roi_multi"]
        no_faces = self.parameters["no_faces"]

        # gather and process all currently relevant detections
        self.detections = [
            x.get_older() for x in self.detections if x.age < blur_memory
        ]  # throw out outdated detections, increase age by 1

        for detection in new_detections:
            if no_faces and detection.kind == "face":
                continue
            scaled_detection = detection.get_scaled(frame.shape, roi_multi)
            scaled_detection.age = 0
            self.detections.append(scaled_detection)

        if len(self.detections) < 1:
            # there are no detections for this frame, leave early and return the same input-frame
            return frame

        # prepare copy and mask
        blur_1 = cv2.GaussianBlur(frame, (blur_size, blur_size), 0)
        # blurring again with the same kernel is the same as blurring with a kernel sqrt(2) as big (but should be faster)
        # the variance of a kernel with size N is N^2
        # the variance of a kernel with size 2*N is 4*N^2
        # so the necessary variance to add on-top is 3 * N^2, whose root is sqrt(3) * N
        # which is why the size of the second blur is sqrt(3) * N to get double the gaussion blur size
        # but with a smaller kernel, since we already have a blurred image with kernel size=N usable as input
        #
        # from Wikipedia https://en.wikipedia.org/wiki/Gaussian_blur:
        # > Applying successive Gaussian blurs to an image has the same effect as applying a single, larger Gaussian blur,
        # whose radius is the square root of the sum of the squares of the blur radii that were actually applied.
        second_blur_size = int((blur_size * sqrt(3)) // 2 * 2 + 1)  # has to be odd for the Gaussian blur, so ceil or floor are not usable
        blur_2 = cv2.GaussianBlur(blur_1, (second_blur_size, second_blur_size), 0)

        mask_blur_1 = np.full((frame.shape[0], frame.shape[1], 1), 0, dtype=np.uint8)
        mask_blur_2 = np.full((frame.shape[0], frame.shape[1], 1), 0, dtype=np.uint8)

        inner_factor = 0.8
        for detection in self.detections:
            # two-fold blurring: softer blur on the edge of the box to look smoother and less abrupt
            outer_box = detection.bounds
            inner_box = detection.bounds.scale(frame.shape, inner_factor)

            if detection.kind == "plate":
                cv2.rectangle(mask_blur_1, outer_box.pt1(), outer_box.pt2(), color=(255, 255, 255), thickness=-1)
                cv2.rectangle(mask_blur_2, inner_box.pt1(), inner_box.pt2(), color=(255, 255, 255), thickness=-1)
            elif detection.kind == "face":
                center_outer, axes_outer = outer_box.ellipse_coordinates()
                center_inner, axes_inner = inner_box.ellipse_coordinates()
                # add ellipse to mask
                cv2.ellipse(mask_blur_1, center_inner, axes_outer, 0, 0, 360, (255, 255, 255), -1)
                cv2.ellipse(mask_blur_2, center_outer, axes_inner, 0, 0, 360, (255, 255, 255), -1)
            else:
                raise ValueError(f"Detection kind not supported: {detection.kind}")

        # apply mask to blur
        mask_background = cv2.bitwise_not(cv2.bitwise_or(mask_blur_1, mask_blur_2))

        # remove second blur-mask from first blur-mask,
        # so as not to add the second (smaller) blur mask twice to the output
        # https://en.wikipedia.org/wiki/Material_nonimplication
        mask_blur_1 = cv2.bitwise_and(mask_blur_1, cv2.bitwise_not(mask_blur_2))

        background = cv2.bitwise_and(frame, frame, mask=mask_background)
        blurred_1 = cv2.bitwise_and(blur_1, blur_1, mask=mask_blur_1)
        blurred_2 = cv2.bitwise_and(blur_2, blur_2, mask=mask_blur_2)
        blurred = cv2.add(blurred_1, blurred_2)
        return cv2.add(background, blurred)

    def detect_identifiable_information(self: 'VideoBlurrer', images: list) -> List[List[Detection]]:
        """
        Run plate and face detection on an input image
        :param images: input images
        :return: detected faces and plates
        """
        scale = self.parameters["inference_size"]
        results_list = self.detector(images, size=scale).xyxy
        return [
            [
                Detection(
                    Bounds(
                        x_min=det[0],
                        y_min=det[1],
                        x_max=det[2],
                        y_max=det[3]
                    ),
                    score=det[4],
                    kind="plate" if det[5].item() == 0 else "face",
                )
                for det in tensor
            ]
            for tensor in results_list
        ]

    def blur_video(self):
        """
        Write a copy of the input video stripped of identifiable information, i.e. faces and license plates
        """
        # gather inputs from self.parameters
        input_path = self.parameters["input_path"]
        temp_output = f"{os.path.splitext(self.parameters['output_path'])[0]}_copy{os.path.splitext(self.parameters['output_path'])[1]}"
        output_path = self.parameters["output_path"]
        threshold = self.parameters["threshold"]
        quality = self.parameters["quality"]
        batch_size = self.parameters["batch_size"]

        # customize detector
        self.detector.conf = threshold

        # open video file
        with imageio.get_reader(input_path) as reader:

            # get the height and width of each frame for future debug outputs on frame
            meta = reader.get_meta_data()
            fps = meta["fps"]
            duration = meta["duration"]
            length = int(duration * fps)
            audio_present = "audio_codec" in meta

            # save the video to a file
            with imageio.get_writer(
                temp_output, codec="libx264", fps=fps, quality=quality
            ) as writer:

                with tqdm(
                    total=length, desc="Processing video", unit="frames", dynamic_ncols=True
                ) as progress_bar:
                    for frame_batch in chunked(reader, batch_size):
                        frame_buffer = [cv2.cvtColor(frame_read, cv2.COLOR_BGR2RGB) for frame_read in frame_batch]
                        new_detections: List[List[Detection]] = self.detect_identifiable_information(frame_buffer)
                        for frame, detections in zip(frame_buffer, new_detections):
                            frame_blurred = self.apply_blur(frame, detections)
                            frame_blurred_rgb = cv2.cvtColor(frame_blurred, cv2.COLOR_BGR2RGB)
                            writer.append_data(frame_blurred_rgb)
                        progress_bar.update(len(frame_buffer))

        # copy over audio stream from original video to edited video
        if is_installed("ffmpeg"):
            ffmpeg_exe = "ffmpeg"
        else:
            ffmpeg_exe = os.getenv("FFMPEG_BINARY")
            if not ffmpeg_exe:
                print(
                    "FFMPEG could not be found! Please make sure the ffmpeg.exe is available under the environment variable 'FFMPEG_BINARY'."
                )
                return

        if audio_present:
            subprocess.run(
                [
                    ffmpeg_exe,
                    "-y",
                    "-i",
                    temp_output,
                    "-i",
                    input_path,
                    "-c",
                    "copy",
                    "-map",
                    "0:0",
                    "-map",
                    "1:1",
                    "-shortest",
                    output_path,
                ],
                stdout=subprocess.DEVNULL,
            )
            # delete temporary output that had no audio track
            try:
                os.remove(temp_output)
            except Exception as e:
                self.alert.emit(
                    f"Could not delete temporary, muted video. Maybe another process (like a cloud storage service or antivirus) is using it already.\n{str(e)}"
                )
        else:
            os.rename(temp_output, output_path)


def setup_detector(weights_path: str):
    """
    Load YOLOv5 detector from torch hub and update the detector with this repo's weights
    :param weights_path: path to .pt file with this repo's weights
    :return: initialized yolov5 detector
    """
    model = torch.hub.load("ultralytics/yolov5", "custom", weights_path, _verbose=False)
    if torch.cuda.is_available():
        print(f"Using {torch.cuda.get_device_name(torch.cuda.current_device())}.")
        model.cuda()
        torch.backends.cudnn.benchmark = True
    else:
        print("Using CPU.")
    return model


def is_installed(name):
    """
    Check whether an executable is available
    """
    return which(name) is not None
