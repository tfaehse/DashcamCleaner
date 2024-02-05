import imageio


def get_video_information(video_path):
    with imageio.get_reader(video_path) as reader:
        meta = reader.get_meta_data()
    return meta
