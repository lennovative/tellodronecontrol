import os
import glob
import cv2


def get_image_filenames(directory):
    """Find all the PNG image files in a given directory and return their corresponding paths as a sorted list."""
    if not os.path.exists(directory):
        return []
    files_list = glob.glob(os.path.join(directory, "*.png"))
    files_list.sort()
    return files_list


def stitch_images(image_list):
    """Stitch images via the OpenCV image stitcher."""
    try:
        stitcher = cv2.Stitcher_create()
        status, stitched = stitcher.stitch(image_list)
        if status == cv2.Stitcher_OK:
            return stitched
        else:
            print(f"Stitching failed with status code {status}")
            return None
    except Exception as e:
        print(f'Error during stitching process: {e}')
        return None


def load_and_stitch(input_dir, output_dir):
    """Create a series of stitched images and save them to the filesystem."""
    image_paths = get_image_filenames(input_dir)
    if not image_paths:
        print(f"No images available here: {input_dir}")
        return False
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    image_list = []
    for i, image_path in enumerate(image_paths):
        print(f"{image_path}")
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to load image: {image_file}")
            continue
        image_list.append(image)
        if len(image_list) < 2:
            continue
        stitched_image = stitch_images(image_list)
        if not stitched_image is None:
            output_path = os.path.join(output_dir, f"stitching_output_{i}.png")
            cv2.imwrite(output_path, stitched_image)
            print(f"Saved: {output_path}")
        else:
            return False
    return True


def main():
    # Get directories
    base_folder = "output_images"
    recording_id = input("Enter recording id: ").strip()
    input_dir = os.path.join(base_folder, str(recording_id))

    # Do stitching
    stiching_results_dir = os.path.join(input_dir, "stitching_results")
    stitching_successful = load_and_stitch(input_dir, stiching_results_dir)
    if stitching_successful:
        print("Stitching successful.")
    else:
        print("Stitching failed.")


if __name__ == "__main__":
    main()
