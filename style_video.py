import functools
import io
import os

import cv2
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
from PIL import Image


# VIDEO PROCESSING =====================================================
def slice_frames(video_file):
    """ video -> images """
    cap = cv2.VideoCapture(video_file)

    idx = 0
    framecount = 0
    frame_skip = 10
    while cap.isOpened():
        ret, frame = cap.read()
        if ret:
            if idx == frame_skip:
                filename = "test_frames/testframe" + str(framecount) + ".jpg"
                cv2.imwrite(filename, frame)
                framecount += 1
                idx = 0
            else:
                idx += 1
        else:
            break

    cap.release()
    cv2.destroyAllWindows()

    return idx


def combine_frames():
    """images -> frames"""
    image_folder = "output_frames"
    video_filename = "output.mp4"

    images = [img for img in os.listdir(image_folder) if img.endswith(".jpg")]
    frame = cv2.imread(os.path.join(image_folder, images[0]))
    height, width, layers = frame.shape

    video = cv2.VideoWriter(video_filename, 0, 5, (width, height))

    for image in images:
        video.write(cv2.imread(os.path.join(image_folder, image)))

    cv2.destroyAllWindows()
    video.release()


# /VIDEO PROCESSING ==========================================================


def crop_center(image):
    """Returns a cropped square image."""
    shape = image.shape
    new_shape = min(shape[1], shape[2])
    offset_y = max(shape[1] - shape[2], 0) // 2
    offset_x = max(shape[2] - shape[1], 0) // 2
    image = tf.image.crop_to_bounding_box(
        image, offset_y, offset_x, new_shape, new_shape
    )
    return image


@functools.lru_cache(maxsize=None)
def load_image(image_path, image_size=(256, 256), preserve_aspect_ratio=True):
    """Loads and preprocesses images."""
    # Load and convert to float32 numpy array, add batch dimension, and normalize to range [0, 1].
    img = plt.imread(image_path).astype(np.float32)[np.newaxis, ...]
    if img.max() > 1.0:
        img = img / 255.0
    if len(img.shape) == 3:
        img = tf.stack([img, img, img], axis=-1)
    img = crop_center(img)
    img = tf.image.resize(img, image_size, preserve_aspect_ratio=True)
    return img


def preprocesses_style_image(style_image_path=None):
    style_img_size = (256, 256)
    if not style_image_path:
        style_image_url = "https://upload.wikimedia.org/wikipedia/commons/0/0a/The_Great_Wave_off_Kanagawa.jpg"
        style_image_path = tf.keras.utils.get_file(
            os.path.basename(style_image_url)[-128:], style_image_url
        )

    style_image = load_image(style_image_path, style_img_size)
    style_image = tf.nn.avg_pool(
        style_image, ksize=[3, 3], strides=[1, 1], padding="SAME"
    )

    return style_image


def get_image_path_from_url(image_url):
    image_path = tf.keras.utils.get_file(os.path.basename(image_url)[-128:], image_url)
    return image_path


def get_content_image_from_path(content_image_path):
    output_image_size = 384
    content_img_size = (output_image_size, output_image_size)
    content_image = load_image(content_image_path, content_img_size)

    return content_image


def get_style_transfer(content_image, nframe, style_image, send_image=False):
    fin = open("path_info.txt", "r+")
    path = fin.readline().strip()
    if len(path) > 0:
        os.environ["TFHUB_CACHE_DIR"] = path  # Any folder that you can access
    hub_handle = "https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2"
    hub_module = hub.load(hub_handle)

    outputs = hub_module(tf.constant(content_image), tf.constant(style_image))
    stylized_image = outputs[0]

    img = tf.keras.preprocessing.image.array_to_img(
        tf.squeeze(stylized_image).numpy(), data_format=None, scale=True, dtype=None
    )

    # write PNG in file-object
    if not send_image:
        # img.save("output_frames/outputframe" + str(nframe) + ".jpg")
        img.save("TEST.jpg")
    else:
        return img


# =========================================================


def style_transfer_video(n_frames):
    style_image = preprocesses_style_image()
    for i in range(n_frames):
        content_path = "test_frames/testframe" + str(i) + ".jpg"
        content_image = get_content_image_from_path(content_path)
        get_style_transfer(content_image, i, style_image)


def style_transfer_video_file(fname):
    n_frames = slice_frames(fname)
    style_transfer_video(n_frames)
    combine_frames()