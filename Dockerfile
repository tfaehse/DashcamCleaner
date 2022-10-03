FROM ubuntu:20.04

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

COPY requirements.txt .

RUN apt-get update && \
    apt-get install --no-install-recommends --yes python3-opencv python3-pip python3-psutil python3-ipython ffmpeg build-essential python3-dev && \
    pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1

COPY src .

VOLUME /input
VOLUME /output

ENTRYPOINT ["python3", "cli.py", "--input_path", "/input", "--output_path", "/output"]
