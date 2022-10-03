FROM ubuntu:22.04

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && \
    apt-get install --no-install-recommends --yes python3-opencv python3-pip python3-psutil python3-ipython ffmpeg && \
    pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1

COPY dashcamcleaner .

VOLUME /input
VOLUME /output

ENTRYPOINT ["python3", "cli.py", "--input_path", "/input", "--output_path", "/output"]
