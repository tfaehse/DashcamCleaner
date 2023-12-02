import multiprocessing as mp
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from shutil import which
from typing import Dict, List, Tuple, Union

import cv2
import imageio
import numpy as np
import torch
from more_itertools import chunked
from src.bounds import Bounds
from src.detection import Detection
from tqdm import tqdm
from ultralytics import YOLO


class VideoBlurrer:
    """
    Video blurrer class
    """
    def __init__(self: "VideoBlurrer", weights_name: str, parameters: Dict[str, Union[bool, int, float, str]]) -> None:
        """
        Constructor
        :param weights_name: file name of the weights to be used
        :param parameters: all relevant paremeters for the blurring process
        """
        self.parameters = parameters
        weights_path = Path(__file__).resolve().parents[1] / "weights" / f"{weights_name}.pt".replace(".pt.pt", ".pt")
        self.detector = setup_detector(weights_path)
        print("Worker created")

    def detect_identifiable_information(self: "VideoBlurrer", images: list) -> List[List[Detection]]:
        """
        Run plate and face detection on an input image
        :param images: input images
        :return: detected faces and plates
        """
        scale = self.parameters["inference_size"]
        threshold = self.parameters["threshold"]
        results_list = self.detector(images, imgsz=[scale], conf=threshold)
        return [
            [
                Detection(
                    Bounds(int(box.xyxy[0][0]), int(box.xyxy[0][1]), int(box.xyxy[0][2]), int(box.xyxy[0][3])),
                    score=float(box.conf),
                    kind="plate" if int(box.cls) == 0 else "face",
                )
                for box in result.boxes
            ]
            for result in results_list
        ]

    def blur_video(self):
        """
        Write a copy of the input video stripped of identifiable information, i.e. faces and license plates
        """
        # gather inputs from self.parameters
        input_path = self.parameters["input_path"]
        output_file = Path(self.parameters["output_path"])
        temp_output = output_file.parent / f"{output_file.stem}_copy{output_file.suffix}"
        output_path = self.parameters["output_path"]
        quality = self.parameters["quality"]
        batch_size = self.parameters["batch_size"]
        blur_workers = min(self.parameters["blur_workers"], mp.cpu_count(), batch_size)

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
            blur_executor = ProcessPoolExecutor(blur_workers)

            # save the video to a file
            with imageio.get_writer(
                temp_output, codec="libx264", fps=fps, quality=quality, macro_block_size=None
            ) as writer:

                with tqdm(total=length, desc="Processing video", unit="frames", dynamic_ncols=True) as progress_bar:
                    for frame_batch in chunked(reader, batch_size):
                        frame_buffer = [cv2.cvtColor(frame_read, cv2.COLOR_BGR2RGB) for frame_read in frame_batch]
                        new_detections: List[List[Detection]] = self.detect_identifiable_information(frame_buffer)
                        args = [
                            [frame, detections, self.parameters]
                            for frame, detections in zip(frame_buffer, new_detections)
                        ]
                        for frame_blurred in blur_executor.map(blur_helper, args):
                            frame_blurred_rgb = cv2.cvtColor(frame_blurred, cv2.COLOR_BGR2RGB)
                            writer.append_data(frame_blurred_rgb)
                        progress_bar.update(len(frame_batch))

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
    Load YOLOv8 detector and update the detector with this repo's weights
    :param weights_path: path to .pt file with this repo's weights
    :return: initialized yolov8 detector
    """
    model = YOLO(weights_path)
    if torch.cuda.is_available():
        print(f"Using {torch.cuda.get_device_name(torch.cuda.current_device())}.")
    else:
        print("Using CPU.")
    return model


def is_installed(name):
    """
    Check whether an executable is available
    """
    return which(name) is not None


def blur_helper(args: Tuple[cv2.Mat, List[Detection], Dict]):
    """
    Free helper function with a single parameter that can be called in a ProcessPoolExecutor
    :param args: List of apply_blur parameters
    :return: Blurred frame
    """

    frame: cv2.Mat
    new_detections: List[Detection]
    parameters: Dict
    frame, new_detections, parameters = args
    return apply_blur(frame, new_detections, parameters)


def apply_blur(frame: cv2.Mat, new_detections: List[Detection], parameters: Dict):
    """
    Apply blur to regions of interests
    :param frame: input image
    :param new_detections: list of newly detected faces and plates
    :return: processed image
    """
    # gather inputs from self.parameters
    blur_size = parameters["blur_size"] * 2 + 1  # must be odd
    roi_multi = parameters["roi_multi"]
    no_faces = parameters["no_faces"]
    feather_dilate_size = parameters["feather_edges"]
    export_mask = parameters["export_mask"]
    export_colored_mask = parameters["export_colored_mask"]

    detections: List[Detection] = []
    for detection in new_detections:
        if no_faces and detection.kind == "face":
            continue
        detections.append(detection.get_scaled(frame.shape, roi_multi))

    # early exit if there are no detections
    if len(detections) < 1:
        # there are no detections for this frame, leave early
        if export_mask or export_colored_mask:
            # if mask export, return empty mask
            return np.full((frame.shape[0], frame.shape[1], 3), 0, dtype=np.uint8)
        else:
            # if not mask export, return the input-frame
            return frame

    # mark all pixels that should be blurred
    blur_area = np.full((frame.shape[0], frame.shape[1], 3), 0, dtype=np.float64)
    mask_color = [1, 1, 1]
    for detection in detections:
        bounds = detection.bounds.expand(frame.shape, feather_dilate_size)
        if detection.kind == "plate":
            cv2.rectangle(blur_area, bounds.pt1(), bounds.pt2(), color=mask_color, thickness=-1)
        elif detection.kind == "face":
            center, axes = bounds.ellipse_coordinates()
            cv2.ellipse(blur_area, center, axes, 0, 0, 360, color=mask_color, thickness=-1)
        else:
            raise ValueError(f"Detection kind not supported: {detection.kind}")

    # blur out mask edges if desired
    if feather_dilate_size > 0:
        blurred_area = cv2.blur(blur_area, (feather_dilate_size, feather_dilate_size), 0)
    else:
        blurred_area = blur_area

    # another early exit: return mask
    if export_mask:
        return (blur_area * 255).astype(np.uint8)

    # blend blurred and unedited frame
    clear_area = np.full((frame.shape[0], frame.shape[1], 3), 1, dtype=np.float64) - blurred_area
    blurred_image = cv2.blur(frame, (blur_size, blur_size), 0)
    frame = clear_area * frame + blurred_area * blurred_image

    return frame.astype(np.uint8)
