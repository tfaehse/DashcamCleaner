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
        feather_dilate_size = self.parameters["feather_edges"]

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

        # convert to float, since the mask needs to be in range [0, 1] and in float
        frame = np.float64(frame)

        # prepare copy and mask
        blur = cv2.GaussianBlur(frame, (blur_size, blur_size), 0)
        blur_mask = np.full((frame.shape[0], frame.shape[1], 3), 0, dtype=np.float64)
        blur_mask_expanded = np.full((frame.shape[0], frame.shape[1], 3), 0, dtype=np.float64)
        mask_color = (1, 1, 1)

        for detection in self.detections:
            bounds_list = [detection.bounds]
            mask_list = [blur_mask]
            if feather_dilate_size > 0:
                bounds_list.append(detection.bounds.expand(frame.shape, feather_dilate_size))
                mask_list.append(blur_mask_expanded)

            for bounds, mask in zip(bounds_list, mask_list):
                # add detection bounds to mask
                if detection.kind == "plate":
                    cv2.rectangle(mask, bounds.pt1(), bounds.pt2(), color=mask_color, thickness=-1)
                elif detection.kind == "face":
                    center, axes = bounds.ellipse_coordinates()
                    # add ellipse to mask
                    cv2.ellipse(mask, center, axes, 0, 0, 360, color=mask_color, thickness=-1)
                else:
                    raise ValueError(f"Detection kind not supported: {detection.kind}")

        if feather_dilate_size > 0:
            # blur mask, to feather its edges
            feather_size = (feather_dilate_size * 3) // 2 * 2 + 1
            blur_mask_feathered = cv2.GaussianBlur(blur_mask_expanded, (feather_size, feather_size), 0)
            blur_mask = cv2.min(cv2.add(blur_mask, blur_mask_feathered), mask_color)  # do not oversaturate blurred regions, limit mask to max-value of 1 (for all three channels)

        # to get the background, invert the blur_mask, i.e. 1 - mask on a matrix per-element level
        mask_background = cv2.subtract(np.full((frame.shape[0], frame.shape[1], 3), mask_color[0], dtype=np.float64), blur_mask)

        background = cv2.multiply(frame, mask_background)
        blurred = cv2.multiply(blur, blur_mask)
        return np.uint8(cv2.add(background, blurred))

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
