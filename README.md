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
        <li><a href="#installation-example-on-windows-using-conda">Installation example on Windows using Conda</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#weights">Weights</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

This project is a result of data protection laws that require identifiable information to be censored in media that is posted to the internet. Dashcam videos in particular tend to be fairly cumbersome to manually edit, so this tool aims to automate the task.

The goal is to release a simple to use application with simple settings and acceptable performance that does not require any knowledge about image processing, neural networks or even programming as a whole on the end user's part.

Development started with an MVP using understand.ai's [Anonymizer](https://github.com/understand-ai/anonymizer) for its backend. Since then, the project has moved on to a custom-trained [YOLOv5](https://github.com/ultralytics/yolov5) network. I wrote about my experiences training the network and generating training data on [Towards Data Science](https://towardsdatascience.com/making-dashcam-videos-gdpr-compliant-f9832883fe94).

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites

You need a working Python environment with a Python version of 3.8 or higher that satisfies the listed `requirements.txt`. Depending on your machine, you can leverage GPU acceleration for pytorch - see [here](https://pytorch.org/get-started/locally/) or just use `requirements-gpu.txt`.


Since OpenCV does not care about audio channels, ffmpeg is used to combine the edited video and the audio channel of the input video. The environment variable `FFMPEG_BINARY` needs to be set to the ffmpeg executable for this to work.

### Installation example on Windows using Conda

1. Clone the repo
   ```sh
   git clone https://github.com/tfaehse/DashcamCleaner.git
   ```
2. Set up Python environment and install requisites
   ```sh
   conda create -n py38 python=3.8
   conda activate py38
   pip install -r requirements.txt
   ```
3. Install ffmpeg binaries (release essentials is enough) and create an environment variable "FFMPEG_BINARY" that points to the ffmpeg.exe binary.
<!-- USAGE EXAMPLES -->
## Usage
On first launch, the YOLOv5 model is automatically downloaded and fused with the custom weights for face and plate detection from this repo.

![UI screenshot](img/ui_screenshot.jpg "Screenshot of the UI")

The UI is fairly self-explanatory: To use the tool, you need to:
- choose an input video file
- choose an output location
- hit start!

The options adjust parameters of the detection algorithm and post-processing options laid out in [the roadmap](Roadmap). The detection threshold and inference size are direct parameters of the YOLOv5 detector, they provide the main controls for detection quality and speed that can be tweaked. In short:
- Each recognized object, i.e. a face or a license plate, possesses a confidence value that describes how likely it is to actually be a license plate or a face. Increasing the threshold results in fewer false positives, at the cost of potential false negatives
- The performance of the detector depends on the input size of the image, so the resolution of the video. The inference size option allows downscaling the input for detections only. The result is faster detection with reduced precision. _NOTE:_ The output video still uses the full resolution from the input video, there is no loss in quality! Only detection runs at a lower resolution.

The blur size determines how strongly detected faces and license plates are blurred. Boxes around faces and license plates can be enlarged by a factor between 0.8 and 10 using the ROI enlargement dial.

Sometimes, a license plate might be missed for just one frame. This one frame, usually 1/30th of a second long, still means the license plate or face could easily be identified - a computationally very cheap (as opposed to increasing the inference scale) way to fix such false negatives can be the frame memory option. In essence, it blurs not only the detected boxes in the current frame, it also blurs regions that were detected in __n__ frames before. Especially in combination with ROI enlargement and videos without very quick movement, this method can hide away missed detections.

For reference: even at 1080p inference, i.e. an inference scale of 1, a 1080p30fps video from my 70mai 1S processes at around 10 frames per second, a 1 minute clip takes ~3 minutes to blur on a 5820K/GTX1060 machine.

There's now also a fairly simple CLI to blur a video:

```
python cli.py -h
usage: cli.py [-h] -i INPUT -o OUTPUT [-w WEIGHTS] [-s [1,1024]] [-b [1-99]] [-if [144-2160]]
              [-t [0-1]] [-r [0-2]] [-q [1, 10]] -f [0-5] [-nf]

This tool allows you to automatically censor faces and number plates on dashcam footage.

options:
  -h, --help                        show this help message and exit

required arguments:
  -i, --input INPUT                 input video file path
  -o, --output OUTPUT               output video file path

optional arguments:
  -w, --weights WEIGHTS             Weights file to use. See readme for the differences
  -s, --batch_size [1,1024]         inference batch size - large values require a lof of memory and
                                    may cause crashes!
  -b, --blur_size [1-99]            granularity of the blurring filter
  -if, --inference_size [144-2160]  vertical inference size, e.g. 1080 or 720
  -t, --threshold [0-1]             detection threshold
  -r, --roi_multi [0-2]             increase/decrease area that will be blurred - 1 means no change
  -q, --quality [1, 10]             quality of the resulting video. higher = better, default: 10
  -f, --frame_memory [0-5]          blur objects in the last x frames too
  -nf, --no_faces                   do not censor faces
```
For now, there are no default values and all parameters have to be provided (in order). There's also no progress bar yet, but there should be an error/success message as soon as blurring is finished/has encountered any issues.

<!-- WEIGHTS -->
## Weights

DashcamCleaner now supports loading weights dynamically, differently trained networks can be selected in the user interface. As part of this change, I will distribute trained networks for German roads with different training parameters over the next weeks:
- different training image resolutions
- different network depths, i.e. YOLOv5's small and medium definitions
- training with (_mosaic) and without (_rect) yolov5's mosaic dataloader.

Once this is completed, I intend to publish an analysis on how training and inference image size and network depth affect performance and quality of the program.

As a rule of thumb:
- bigger images lead to better detection of small objects, for both training and inference
- deeper networks have a higher ceiling for object detection but slow down training and inference
- lowering inference image size can dramatically speed up the program
- the mosaic dataloader makes a large, positive impact. This was slightly unexpected for me, I assumed the (higher) resolution of fixed-size training would improve results, given that lots of objects are very small

In summary, you should select the highest inference image size you can afford. Definitely go for the _mosaic weights. The impact of higher training image sizes and deeper networks will be investigated once training has been completed!

<!-- ROADMAP -->
## Roadmap

With the transition to a custom YOLOv5 detector, the original targets for the tool have been met. Performance is satisfactory and detection quality is very promising. However, work remains:
- further trained networks and an analysis of different network sizes and image sizes used for training
- release standalone executable

Implemented post processing steps:
- a "frame memory": plate and face positions from the last n frames are also blurred → useful for static plates/faces
- enlarging of blurred regions → useful in combination with frame memory - most single missed frames can be captured this way, unless very quick movement is happening


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

* YOLOv5 was chosen for its combination of performance, speed and ease of use
* The original prototype was essentially a wrapper for Anonymizer, and the current implementation wouldn't have been possible without its high quality labels.