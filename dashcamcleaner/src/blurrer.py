import os
from itertools import islice
from shutil import which

import cv2
import numpy as np
import torch
from src.box import Box
from src.video_utils import VideoReader, VideoWriter
from tqdm import tqdm


def batch_iter(iterable, batch_size):
    iterator = iter(iterable)
    while batch := list(islice(iterator, batch_size)):
        yield batch


class VideoBlurrer:
    def __init__(self, weights_name, parameters):
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

    def apply_blur(self, frame: np.array, new_detections: list):
        """
        Apply Gaussian blur to regions of interests
        :param frame: input image
        :param new_detections: list of newly detected faces and plates
        :return: processed image
        """
        # gather inputs from self.parameters
        blur_size = self.parameters["blur_size"]
        blur_memory = self.parameters["blur_memory"]
        roi_multi = self.parameters["roi_multi"]
        no_faces = self.parameters["no_faces"]

        # gather and process all currently relevant detections
        self.detections = [
            [x[0], x[1] + 1] for x in self.detections if x[1] <= blur_memory
        ]  # throw out outdated detections, increase age by 1
        for detection in new_detections:
            if no_faces and detection.kind == "face":
                continue
            scaled_detection = detection.scale(frame.shape, roi_multi)
            self.detections.append([scaled_detection, 0])

        # prepare copy and mask
        temp = frame.copy()
        mask = np.full((frame.shape[0], frame.shape[1], 1), 0, dtype=np.uint8)

        for detection in [x[0] for x in self.detections]:
            # two-fold blurring: softer blur on the edge of the box to look smoother and less abrupt
            outer_box = detection
            inner_box = detection.scale(frame.shape, 0.8)

            if detection.kind == "plate":
                # blur in-place on frame
                frame[outer_box.coords_as_slices()] = cv2.blur(
                    frame[outer_box.coords_as_slices()], (blur_size, blur_size)
                )
                frame[inner_box.coords_as_slices()] = cv2.blur(
                    frame[inner_box.coords_as_slices()], (blur_size * 2 + 1, blur_size * 2 + 1)
                )

            elif detection.kind == "face":
                center, axes = detection.ellipse_coordinates()
                # blur rectangle around face
                temp[outer_box.coords_as_slices()] = cv2.blur(
                    temp[outer_box.coords_as_slices()], (blur_size * 2 + 1, blur_size * 2 + 1)
                )
                # add ellipse to mask
                cv2.ellipse(mask, center, axes, 0, 0, 360, (255, 255, 255), -1)

            else:
                raise ValueError(f"Detection kind not supported: {detection.kind}")

        # apply mask to blur faces too
        mask_inverted = cv2.bitwise_not(mask)
        background = cv2.bitwise_and(frame, frame, mask=mask_inverted)
        blurred = cv2.bitwise_and(temp, temp, mask=mask)
        return cv2.add(background, blurred)

    def detect_identifiable_information(self, images: list):
        """
        Run plate and face detection on an input image
        :param images: input images
        :return: detected faces and plates
        """
        scale = self.parameters["inference_size"]
        results_list = self.detector(images, size=scale).xyxy
        return [
            [
                Box(
                    det[0],
                    det[1],
                    det[2],
                    det[3],
                    det[4],
                    "plate" if det[5].item() == 0 else "face",
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
        output_path = self.parameters["output_path"]
        threshold = self.parameters["threshold"]
        quality = self.parameters["quality"]
        batch_size = self.parameters["batch_size"]
        stabilize = self.parameters["stabilize"]

        # customize detector
        self.detector.conf = threshold

        # open video file
        with VideoReader(input_path, stabilize) as reader:

            # get the height and width of each frame for future debug outputs on frame
            meta = reader.get_metadata()
            print(meta)

            # save the video to a file
            with VideoWriter(
                output_path, input_path, meta["fps"], meta["width"], meta["height"], quality
            ) as writer:

                with tqdm(
                    total=meta["frames"], desc="Processing video", unit="frames", dynamic_ncols=True
                ) as progress_bar:

                    for batch in batch_iter(reader, batch_size):
                        new_detections = self.detect_identifiable_information(batch)
                        for frame, detections in zip(batch, new_detections):
                            frame = self.apply_blur(frame, detections)
                            writer.write_frame(frame)
                        progress_bar.update(len(batch))


def setup_detector(weights_path: str):
    """
    Load YOLOv5 detector from torch hub and update the detector with this repo's weights
    :param weights_path: path to .pt file with this repo's weights
    :return: initialized yolov5 detector
    """
    model = torch.hub.load("ultralytics/yolov5", "custom", weights_path, _verbose=False)
    if torch.cuda.is_available():
        print(
            f"Using {torch.cuda.get_device_name(torch.cuda.current_device())} with {weights_path}."
        )
        model.cuda()
        torch.backends.cudnn.benchmark = True
    else:
        print(f"Using CPU with {weights_path}.")
    return model


def is_installed(name):
    """
    Check whether an executable is available
    """
    return which(name) is not None
