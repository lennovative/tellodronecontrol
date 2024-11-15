import cv2
import pygame
import numpy as np
import time
import os
import glob
from stitching import Stitcher  # Assuming this is your custom stitching module

def get_image_filenames(directory):
    files_list = glob.glob(os.path.join(directory, "*.jpg"))
    files_list.sort()
    return files_list

def resize_image(img, scale_factor=0.3):
    new_width = int(img.shape[1] * scale_factor)
    new_height = int(img.shape[0] * scale_factor)
    new_size = (new_width, new_height)
    result = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
    return result

def stitch_images(stitcher, images):
    if len(images) < 2:
        return None
    try:
        stitched_image = stitcher.stitch(images)
        return stitched_image
    except Exception as e:
        print(e)
        return None

def display_image_pygame(screen, image, title="Image"):
    # Convert the OpenCV image (BGR) to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_surface = pygame.surfarray.make_surface(np.rot90(image_rgb))
    # Scale the image to fit the Pygame window
    image_surface = pygame.transform.scale(image_surface, screen.get_size())
    screen.blit(image_surface, (0, 0))
    pygame.display.set_caption(title)
    pygame.display.update()

def image_stitching_test(stitcher, path_to_test_images, screen):
    image_files = get_image_filenames(path_to_test_images)
    images = []
    final_result = None

    for image_file in image_files:
        print(image_file)
        image_raw = cv2.imread(image_file)
        image = resize_image(image_raw)

        if image is None:
            print(f"Failed to load image: {image_file}")
            continue

        # Display the current image in Pygame
        display_image_pygame(screen, image, title="Current Image")

        # Add the new image to the list of images to stitch
        images.append(image)

        # Attempt to stitch the images together
        stitched_image = stitch_images(stitcher, images)

        # Display the stitching progress
        if stitched_image is not None:
            final_result = stitched_image.copy()
            display_image_pygame(screen, stitched_image, title="Stitching Progress")
            time.sleep(0.5)  # Delay to simulate processing time

    print("Stitching complete.")
    return final_result

def main():
    # Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((960, 720))  # Set window size for the display
    pygame.display.set_caption("Image Stitching")

    # Initialize the stitcher
    stitcher = Stitcher(confidence_threshold=0.1)

    # Path to test images
    path_to_test_images = "../Test_images/2"

    # Run the stitching test and display the final result
    stitched_image = image_stitching_test(stitcher, path_to_test_images, screen)

    # Display final result
    if stitched_image is not None:
        display_image_pygame(screen, stitched_image, title="Final Result")

    # Wait until the user closes the window
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        pygame.display.update()
        time.sleep(0.1)

    pygame.quit()

if __name__ == "__main__":
    main()
