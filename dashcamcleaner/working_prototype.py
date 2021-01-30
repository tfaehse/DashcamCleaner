# -*- coding: utf-8 -*-
import os
import sys

import cv2
import numpy as np
from PIL import Image

# hack to add Anonymizer submodule to PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "anonymizer"))
from anonymizer.anonymization.anonymizer import Anonymizer
from anonymizer.detection.detector import Detector
from anonymizer.detection.weights import download_weights, get_weights_path
from anonymizer.obfuscation.obfuscator import Obfuscator
from tqdm import tqdm
from math import floor, ceil


def cv2_to_npimage(cv2_image: np.ndarray):
    cv2_im = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    pil_im = Image.fromarray(cv2_im)
    np_image = np.array(pil_im)
    return np_image


def npimage_to_cv2(np_image):
    np_array = np.array(np_image)
    return cv2.cvtColor(np_array, cv2.COLOR_RGB2BGR)


def setup_anonymizer(weights_path: str, face_threshold: float, plate_threshold: float, obfuscation_parameters: str):
    """
    Sets up and configures an Anonymizer object
    :param weights_path: directory to Anonymizer's weights
    :param face_threshold: threshold for face detection
    :param plate_threshold: threshold for plate detection
    :param obfuscation_parameters: parameters for Gaussian blur
    :return: Anonymizer object
    """
    download_weights(download_directory=weights_path)

    kernel_size, sigma, box_kernel_size = obfuscation_parameters.split(',')
    obfuscator = Obfuscator(kernel_size=int(kernel_size), sigma=float(sigma), box_kernel_size=int(box_kernel_size))
    detectors = {
        'face': Detector(kind='face', weights_path=get_weights_path(weights_path, kind='face')),
        'plate': Detector(kind='plate', weights_path=get_weights_path(weights_path, kind='plate'))
    }
    return Anonymizer(obfuscator=obfuscator, detectors=detectors)


def blur_video(input: str, output: str, anonymizer: Anonymizer, detection_thresholds: dict):
    cap = cv2.VideoCapture(input)

    # gets the height and width of each frame
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # saves the video to a file
    fourcc = cv2.VideoWriter_fourcc(*'H264')
    writer = cv2.VideoWriter(output, fourcc, 30, (width, height))

    progress = tqdm(total=length)

    # to make video actual speed
    if cap.isOpened() == False:
        print('error file not found')

    # while the video is running the loop will keep running
    while cap.isOpened():
        # returns each frame
        ret, frame = cap.read()

        # if there are still frames keeping showing the video
        if ret == True:
            # apply Anonymizer's magic
            np_frame = cv2_to_npimage(frame)
            _, detections = anonymizer.anonymize_image(image=np_frame, detection_thresholds=detection_thresholds)
            for detection in detections:
                x_min = floor(detection.y_min)
                x_max = ceil(detection.y_max)
                y_min = floor(detection.x_min)
                y_max = ceil(detection.x_max)
                frame[x_min:x_max, y_min:y_max] = cv2.blur(frame[x_min:x_max, y_min:y_max], (30, 30))
            writer.write(frame)

            # will stop the video if it fnished or you press q
            if cv2.waitKey(10) & 0xff == ord('q'):
                break
        else:
            break
        progress.update()
    progress.close()

    # stop the video, and gets rid of the window that it opens up
    cap.release()
    writer.release()


if __name__ == "__main__":
    anonymizer = setup_anonymizer("weights", .3, .1, "1, 0, 1")
    detection_thresholds = {
        'face': .3,
        'plate': .1
    }
    blur_video("vid.mp4", "blurred.mkv", anonymizer, detection_thresholds)
    print("OK")
