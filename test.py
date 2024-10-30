import cv2
from stitching import Stitcher
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import clear_output, display
import time
import os
import glob


def get_image_filenames(directory):
    files_list = glob.glob(os.path.join(directory, "*.jpg"))
    files_list.sort()
    return files_list


# Function to display the stitched image in real-time
def display_image(image, title="Image"):
    clear_output(wait=True)
    plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    plt.title(title)
    plt.axis('off')
    display(plt.gcf())
    plt.pause(1)


def stitch_images(stitcher, images):
    if len(images) < 2:
        return None
    try:
        stitched_image = stitcher.stitch(images)
        return stitched_image
    except Exception as e:
        print(e)
        return None


def resize_image(img, scale_factor=0.3):
    new_width = int(img.shape[1] * scale_factor)
    new_height = int(img.shape[0] * scale_factor)
    new_size = (new_width, new_height)
    result = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
    return result


def image_stiching_test(stitcher, path_to_test_images):
    image_files = get_image_filenames(path_to_test_images)
    images = []
    final_result = None

    # Real-time stitching process
    for image_file in image_files:
        print(image_file)
        image_raw = cv2.imread(image_file)
        image = resize_image(image_raw)
        if image is None:
            print(f"Failed to load image: {image_file}")
            continue
        display_image(image, title="Current Image")
        # Add the new image to the list of images to stitch
        images.append(image)
        stitched_image = stitch_images(stitcher, images)
        if stitched_image is not None:
            final_result = stitched_image.copy()
            display_image(stitched_image, title="Stitching Progress")
            #images = [stitched_image]
        # Simulate delay
        time.sleep(0.2)
    print("Stitching complete.")
    return final_result


def main():
    # Initialize the OpenCV stitcher
    #stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
    stitcher = Stitcher(confidence_threshold=0.05)
    # Testing
    path_to_test_images = "../Test_images"
    stitched_image = image_stiching_test(stitcher, path_to_test_images)
    if stitched_image is not None:
        display_image(stitched_image, title="Final Result")
        time.sleep(5)



if __name__ == "__main__":
    main()
