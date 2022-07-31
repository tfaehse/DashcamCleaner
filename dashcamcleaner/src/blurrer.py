import os
import subprocess
from shutil import which
from tqdm import tqdm

import cv2
import imageio
import numpy as np
import torch
from src.box import Box


class VideoBlurrer:
    def __init__(self, weights_name, parameters=None):
        """
        Constructor
        :param weights_name: file name of the weights to be used
        :param parameters: all relevant paremeters for the blurring process
        """
        self.parameters = parameters
        self.detections = []
        weights_path = os.path.join("weights", f"{weights_name}.pt".replace(".pt.pt", ".pt"))
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

            # save the video to a file
            with imageio.get_writer(
                temp_output, codec="libx264", fps=fps, quality=quality
            ) as writer:

                with tqdm(total=length, desc="Processing video", unit="frames") as progress_bar:
                    buffer = []

                    for frame_read in reader:
                        rgb_frame = cv2.cvtColor(frame_read, cv2.COLOR_BGR2RGB)
                        if len(buffer) < batch_size:
                            buffer.append(rgb_frame)
                        else:
                            # buffer is full - detect information for all images in buffer
                            new_detections = self.detect_identifiable_information(buffer)
                            for frame, detections in zip(buffer, new_detections):
                                frame = self.apply_blur(frame, detections)
                                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                writer.append_data(frame_rgb)
                            progress_bar.update(len(buffer))
                            buffer = [rgb_frame]

                    # Detect information for the rest of the buffer
                    new_detections = self.detect_identifiable_information(buffer)
                    for frame, detections in zip(buffer, new_detections):
                        frame = self.apply_blur(frame, detections)
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        writer.append_data(frame_rgb)
                    progress_bar.update(len(buffer))

        # copy over audio stream from original video to edited video
        if is_installed("ffmpeg"):
            ffmpeg_exe = "ffmpeg"
        else:
            ffmpeg_exe = os.getenv("FFMPEG_BINARY")
            if not ffmpeg_exe:
                print(
                    "FFMPEG could not be found! Please make sure the ffmpeg.exe is available under the envirnment variable 'FFMPEG_BINARY'."
                )
                return
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
            print(
                f"Could not delete temporary, muted video. Maybe another process (like a cloud service or antivirus) is using it already. \n{str(e)}"
            )


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
