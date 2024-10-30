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
    plt.pause(0.1)


def stitch_images(stitcher, images):
    if len(images) < 2:
        return
    #status, stitched_image = stitcher.stitch(images)
    stitched_image = stitcher.stitch(images)

    #if status == cv2.Stitcher_OK:
    #    display_image(stitched_image, title="Stitching Progress")
    #else:
    #    print("Stitching failed with status code:", status)

    display_image(stitched_image, title="Stitching Progress")


def image_stiching_test(stitcher, path_to_test_images):
    image_files = get_image_filenames(path_to_test_images)
    images = []

    # Real-time stitching process
    for image_file in image_files:
        image = cv2.imread(image_file)
        print(image_file)
        if image is None:
            print(f"Failed to load image: {image_file}")
            continue
        #display_image(image, title="Current Image")
        # Add the new image to the list of images to stitch
        images.append(image)
        stitch_images(stitcher, images)
        # Simulate delay
        time.sleep(1)
    print("Stitching complete.")


def main():
    # Initialize the OpenCV stitcher
    #stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
    stitcher = Stitcher(confidence_threshold=0.1)
    # Testing
    path_to_test_images = "../Test_images"
    image_stiching_test(stitcher, path_to_test_images)



if __name__ == "__main__":
    main()
