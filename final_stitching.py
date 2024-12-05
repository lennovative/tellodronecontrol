import os
import glob
import cv2
from stitching import Stitcher


def get_image_filenames(directory):
    files_list = glob.glob(os.path.join(directory, "*.png"))
    files_list.sort()
    return files_list


def stitch_image_other(stitcher, images):
    if len(images) < 2:
        return None
    try:
        stitched_image = stitcher.stitch(images)
        return stitched_image
    except Exception as e:
        print(e)
        return None

def stitch_images(images):
    stitcher = cv2.Stitcher_create()
    status, stitched = stitcher.stitch(images)
    if status == cv2.Stitcher_OK:
        return stitched
    else:
        print(f"Stitching failed with status code {status}")
        return None


def group_image_paths(image_paths):
    result = {}
    for image_path in image_paths:
        key = os.path.basename(image_path).split("_", 1)[0]
        if key not in result:
            result[key] = []
        result[key].append(image_path)
    return result


def load_and_stitch(image_paths, output_dir):
    if not image_paths: return
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    images = []
    for i, image_path in enumerate(image_paths):
        print(f"Working on {image_path}")
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to load image: {image_file}")
            continue
        images.append(image)
        stitched_image = stitch_images(images)
        if stitched_image is not None:
            cv2.imwrite(os.path.join(output_dir, f"stitching_output_{i}.png"), stitched_image)
            print(f"Saved: {output_dir}")

def main():
    # Init stitcher
    #stitcher = Stitcher(confidence_threshold=0.1)
    input_dir = "./output_images"
    all_image_paths = get_image_filenames(input_dir)
    image_paths_grouped = group_image_paths(all_image_paths)
    output_dir = "./output_images/stitching"
    for key, value in image_paths_grouped.items():
        load_and_stitch(value, os.path.join(output_dir, key))
    print("done")



if __name__ == "__main__":
    main()
