<br />
<p align="center">
  <h3 align="center">DashcamCleaner</h3>

  <p align="center">
    This tool allows you to automatically censor faces and number plates on dashcam footage.
    <br />
    <a href="https://github.com/tfaehse/DashcamCleaner/issues">Report Bug</a>
    ·
    <a href="https://github.com/tfaehse/DashcamCleaner/issues">Request Feature</a>
  </p>
</p>



<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary><h2 style="display: inline-block">Table of Contents</h2></summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

This project is a result of data protection laws that require identifiable information to be censored in media that is posted to the internet. Dashcam videos in particular tend to be fairly cumbersome to manually edit, so this tool aims to automate the task. Thus, it offers a simple Qt GUI in Python that apply's understand-ai's [Anonymizer](https://github.com/understand-ai/anonymizer) to each frame of an input video. 

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites

You need a working Python 3.6 environment that satisfies the listed `requirements.txt`.

`tensorflow-gpu==1.11.0` requires a CUDA GPU and a properly set up CUDA environment. [This](https://towardsdatascience.com/installing-tensorflow-with-cuda-cudnn-and-gpu-support-on-windows-10-60693e46e781) excellent writeup details the installation. If you do not have access to such hardware, you can replace the requirement with `tensorflow==1.11.0` to rely on pure CPU processing, expect performance to suffer without GPU acceleration though.

Further, h264 was chosen for the output video file. You can download an open source library to add support [here](https://github.com/cisco/openh264/releases).

### Installation

1. Clone the repo
   ```sh
   git clone --recurse-submodules https://github.com/tfaehse/DashcamCleaner.git
   ```
2. Set up Python environment and install requisites
   ```sh
   conda create -n py36 python=3.6
   conda activate py36
   pip install -r requirements.txt
   ```

<!-- USAGE EXAMPLES -->
## Usage
On first launch, Anonymizer has to download its neural net weights, this might take a minute. 


![UI screenshot](img/ui_screenshot.jpg "Screenshot of the UI")

The UI is fairly self-explanatory: To use the tool, you need to:
- choose an input video file
- choose an output location
- hit start!

The options adjust the resulting video's frames per second, the frame memory optimization laid out in [the roadmap](Roadmap). Blur size, face and plate thresholds are Anonymizer parameters - they adjust the size of the Gaussian blur and the detection thresholds for the detector. 

Experience has shown that Anonymizer's blurring algorithm, while producing beautiful results, can get a bit slow for larger resolutions. Checking the custom blur radio button results in a much simpler and faster OpenCV solution. Increasing the area to be blurred and using ROI info from previous frames is only possible using this method.

For reference: a 1080p30fps video from my 70mai 1S is blurred at around 1,2 frames per second, ie a 1 minute clip takes <30 minutes to blur on a 5820K/GTX1060. Not perfect, but it removes a lot of manual labor :) 


<!-- ROADMAP -->
## Roadmap
As of now, each frame is treated individually. Issues arise when a plate or a face is missed by Anonymizer in a single frame, as it will be clearly visible in the video and require manual correction. Possible ideas to combat this behavior include:
- a "frame memory": plate and face positions from the last n frames are also blurred → implemented, useful for static plates/faces
- proper plate/face tracking across frames
- enlarging of blurred regions → implemented, useful in combination with frame memory - most single missed frames can be captured this way, unless very quick movement is happening
- "light" frame tracking, i.e. first getting all ROI positions for the whole video using Anonymizer (still on a per-frame basis) and using static analysis to establish links between ROIs across frames with the goal of approximating the position of missed frames


<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.



<!-- CONTACT -->
## Contact

Thomas Fähse - tfaehse@me.com

Project Link: [https://github.com/tfaehse/DashcamCleaner](https://github.com/tfaehse/DashcamCleaner)



<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements

* As this project is essentially a wrapper for Anonymizer, none of this would be possible without it