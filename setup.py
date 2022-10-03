import os
from setuptools import setup

readme = os.path.join(os.path.dirname(__file__), "README.md")
with open(readme, "r") as f:
    long_description = f.read()

setup(
    name='dashcamcleaner',
    version='0.2.1',
    description='Blur license plates and faces in videos',
    url='https://github.com/tfaehse/DashcamCleaner',
    author='Thomas Fähse',
    author_email='tfaehse@me.com',
    license='MIT',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=['dashcamcleaner'],
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        "opencv-python>=4.5.3.56,<=4.6.0.66",
        "pandas>=1.4.3,<=1.5.0",
        "imageio==2.22.1",
        "imageio-ffmpeg==0.4.7",
        "ipython>=8.0.0,<=8.5.0",
        "psutil>=5.6.4,<=5.9.2",
        "more_itertools>=8.1.0,<=8.14.0",
        "Pillow>=8.1.1,<=9.2.0",
        "PySide6>=6.3.0,<=6.3.2",
        "PyYAML>=6.0",
        "requests>=2.28.0",
        "scipy>=1.7.3,<=1.9.1",
        "seaborn>=0.11.2,<=0.12.0",
        "tensorboard==2.10.1",
        "torch==1.12.1",
        "torchaudio==0.12.1",
        "torchvision==0.13.1",
        "tqdm"
    ],

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
