import ast
import json
import multiprocessing as mp
import os
import re
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from shutil import which
from typing import Dict, List, Tuple, Union

import cv2
import imageio
import numpy as np
import pandas as pd
import torch
from more_itertools import chunked
from src.tracking import BoxTracker
from src.utils.bounds import Bounds
from src.utils.detection import Detection
from src.utils.progress_handler import ProgressHandler
from src.utils.utils import get_video_information
from ultralytics import YOLO


def run_if_alive(fn):
    """
    Decorator to only execute fn when self._abort is not set
    :param fn: function to decorate
    :return: fn if abort is not set
    """

    def decorator(self, *args, **kwargs):
        if self._abort is True:
            return
        return fn(self, *args, **kwargs)

    return decorator


class VideoBlurrer:
    """
    Video blurrer class
    """

    def __init__(
        self: "VideoBlurrer",
        progress_handler: ProgressHandler,
        weights_name: str,
        parameters: Dict[str, Union[bool, int, float, str]],
    ) -> None:
        """
        Constructor
        :param weights_name: file name of the weights to be used
        :param progress_handler: handler for reporting progress to the user
        :param parameters: all relevant paremeters for the blurring process
        """
        self.parameters = parameters
        weights_path = Path(__file__).resolve().parents[1] / "weights" / f"{weights_name}.pt".replace(".pt.pt", ".pt")
        self.device, self.detector = self.setup_detector(weights_path)
        self.progress_handler = progress_handler
        self._abort = False
        self.error = ""
        print("Worker created")

    @run_if_alive
    def detect_identifiable_information(self: "VideoBlurrer", images: list) -> List[List[Detection]]:
        """
        Run plate and face detection on an input image
        :param images: input images
        :return: detected faces and plates
        """
        scale = self.parameters["inference_size"]
        results_list = self.detector(images, imgsz=[scale], verbose=False, conf=self.detector.conf, device=self.device)
        return [
            [
                Detection(
                    Bounds(int(box.xyxy[0][0]), int(box.xyxy[0][1]), int(box.xyxy[0][2]), int(box.xyxy[0][3])),
                    score=float(box.conf),
                    kind=result.names[int(box.cls)],
                )
                for box in result.boxes
            ]
            for result in results_list
        ]

    @run_if_alive
    def run_detection(self):
        """
        Run detector on all frames of the input video
        :return: dataframe containing all detections
        """
        # gather inputs from self.parameters
        input_path = self.parameters["input_path"]
        threshold = self.parameters["threshold"]
        batch_size = self.parameters["batch_size"]

        # prepare detection cache
        frame_detections = []

        # customize detector
        self.detector.conf = threshold

        # open video file
        with imageio.get_reader(input_path) as reader:
            # get the height and width of each frame for future debug outputs on frame
            meta = reader.get_meta_data()
            fps = meta["fps"]
            duration = meta["duration"]
            length = int(duration * fps)
            self.progress_handler.init(len=length, unit="frames", desc="Detecting plates and faces...")

            # save the video to a file
            for batch_index, frame_batch in enumerate(chunked(reader, batch_size)):
                if self._abort:
                    break
                frame_buffer = [cv2.cvtColor(frame_read, cv2.COLOR_BGR2RGB) for frame_read in frame_batch]
                for index, detection in enumerate(self.detect_identifiable_information(frame_buffer)):
                    frame_detections += [
                        {"frame": batch_size * batch_index + index} | det.dict_format() for det in detection
                    ]
                self.progress_handler.update(len(frame_batch))
            self.progress_handler.finish()
        return pd.DataFrame(frame_detections)

    def execute_pipeline(self):
        """
        Execute the entire blurring pipeline
        """
        # set up parameters
        video_meta = get_video_information(self.parameters["input_path"])

        # read inference size
        model_name: str = self.parameters["weights"]
        training_inference_size: int = int(re.search(r"(?P<imgsz>\d*)p\_", model_name).group("imgsz"))
        self.parameters["inference_size"] = int(training_inference_size * 16 / 9)

        # run blurrer
        detections = self.run_detection()
        tracking_results = self.track_detections(video_meta, detections)
        if self.parameters["export_json"]:
            self.write_json_dets(tracking_results)

        self.write_video(tracking_results)

    @run_if_alive
    def write_json_dets(self, tracks):
        """
        Write tracking results into a simple JSON file
        :param tracks: dataframe with all tracks
        """
        out = {}
        for frame, obs in tracks.reset_index().groupby("frame"):
            out[frame] = ast.literal_eval(obs.drop(["frame", "index"], axis=1).to_json(orient="records"))
        with open(Path(self.parameters["output_path"]).with_suffix(".json"), "w") as f:
            json.dump(out, f, indent=2)

    @run_if_alive
    def track_detections(self, video_meta: dict, detections: pd.DataFrame):
        """
        Run tracking on raw detections
        :param detections: input detections for all frames
        :return: forward and backward tracking results
        """
        max_distance = int(video_meta["size"][1] * self.parameters["tracking_dist"])
        tracker = BoxTracker(max_distance, self.parameters["tracking_memory"], self.parameters["tracking_memory"])
        forward_tracking = tracker.run_forward_tracking(detections, self.progress_handler)
        backward_tracking = tracker.run_backward_tracking(forward_tracking, self.progress_handler)
        return backward_tracking

    @run_if_alive
    def write_video(self, tracks: pd.DataFrame):
        """
        Write a copy of the input video stripped of identifiable information, i.e. faces and license plates
        :param tracks: tracks of detected boxes
        """
        # gather inputs from self.parameters
        input_path = self.parameters["input_path"]
        output_file = Path(self.parameters["output_path"])
        temp_output = output_file.parent / f"{output_file.stem}_copy{output_file.suffix}"
        threshold = self.parameters["threshold"]
        quality = self.parameters["quality"]
        batch_size = self.parameters["batch_size"]
        blur_workers = min(self.parameters["blur_workers"], mp.cpu_count(), batch_size)

        # prepare detection cache
        track_cache = {
            frame: [Detection.from_row(row) for _, row in tracks.loc[tracks["frame"] == frame].iterrows()]
            for frame in range(tracks["frame"].max())
        }

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
                self.progress_handler.init(len=length, unit="frames", desc="Writing blurred video...")
                for batch_index, frame_batch in enumerate(chunked(reader, batch_size)):
                    if self._abort:
                        break
                    frame_buffer = [cv2.cvtColor(frame_read, cv2.COLOR_BGR2RGB) for frame_read in frame_batch]
                    args = [
                        [frame, global_index, track_cache, self.parameters]
                        for frame, global_index in zip(
                            frame_buffer, [batch_size * batch_index + x for x in range(batch_size)]
                        )
                    ]
                    for frame_blurred in blur_executor.map(blur_helper, args):
                        frame_blurred_rgb = cv2.cvtColor(frame_blurred, cv2.COLOR_BGR2RGB)
                        writer.append_data(frame_blurred_rgb)
                    self.progress_handler.update(len(frame_batch))
        self.progress_handler.finish()

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
                    output_file,
                ],
                stdout=subprocess.DEVNULL,
            )
            # delete temporary output that had no audio track
            try:
                os.remove(temp_output)
            except Exception as e:
                self.error = f"Could not delete temporary, muted video. Maybe another process (like a cloud storage service or antivirus) is using it already.\n{str(e)}"
        else:
            os.rename(temp_output, output_file)

    def setup_detector(self, weights_path: str):
        """
        Load YOLOv8 detector and update the detector with this repo's weights
        :param weights_path: path to .pt file with this repo's weights
        :return: initialized yolov8 detector
        """
        model = YOLO(weights_path)
        device = "cpu"
        if torch.cuda.is_available():
            device = torch.cuda.get_device_name(torch.cuda.current_device())
        elif torch.backends.mps.is_available():
            device = "mps"
        print(f"Using {device}.")
        return device, model


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
    parameters: Dict
    frame, index, detections_dict, parameters = args
    return apply_blur(frame, index, detections_dict, parameters)


def apply_blur(frame: cv2.Mat, index: int, detection_dict: Dict, parameters: Dict):
    """
    Apply blur to regions of interests
    :param frame: input image
    :param index: global frame index for this frame
    :param detection_dict: dictionary with all processed (up to the current batch) detections
    :return: processed image
    """
    # gather inputs from self.parameters
    blur_size = parameters["blur_size"] * 2 + 1  # must be odd
    roi_multi = parameters["roi_multi"]
    no_faces = parameters["no_faces"]
    feather_dilate_size = parameters["feather_edges"]
    export_mask = parameters["export_mask"]
    export_colored_mask = parameters["export_colored_mask"]

    # gather all detections for the current frame
    detections = detection_dict.get(index, [])

    filtered_detections = []
    for detection in detections:
        if no_faces and detection.kind == "face":
            continue
        filtered_detections.append(detection.get_scaled(frame.shape, roi_multi))

    # early exit if there are no detections
    if len(filtered_detections) < 1:
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
    for detection in filtered_detections:
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
