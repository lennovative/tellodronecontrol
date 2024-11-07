from djitellopy import Tello
import cv2
import threading
import time


def start_thread_video_stream(drone, exit_event):
    def video_stream():
        try:
            capture = drone.get_frame_read()
            while not exit_event.is_set():
                frame = capture.frame
                if frame is None:
                    continue
                cv2.imshow("Tello Live Video", frame)
                cv2.waitKey(1)
        except Exception as e:
            print(f"Error in video stream thread: {e}")

        finally:
            cv2.destroyAllWindows()

    # Start video display thread
    thread = threading.Thread(target=video_stream)
    thread.start()
    return thread


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


def start_thread_image_processing(drone, image_stitcher, image_processing_event, exit_event):
    def image_processing():
        images = []
        try:
            capture = drone.get_frame_read()
            while image_processing_event.is_set() and not exit_event.is_set():
                frame = capture.frame
                if frame is None:
                    continue
                images.append(frame)
                stitched_image = stitch_images(image_stitcher, images)
                if stitched_image is not None:
                    display_image(stitched_image, title="Stitching Progress")
                time.sleep(0.25)
        except Exception as e:
            print(f"Error in image processing thread: {e}")

        finally:
            final_stitched_image = stitch_images(image_stitcher, images)
            display_image(final_stitched_image, title="Final Result")
            time.sleep(4)

    thread = threading.Thread(target=image_processing)
    thread.start()
    return thread


def main():
    # Initialize the Tello drone
    drone = Tello()
    drone.connect()
    print(f"Battery level: {drone.get_battery()}%")

    # Initialize image stitching tool
    image_stitcher = Stitcher(confidence_threshold=0.1)

    # Set events
    exit_event = threading.Event()
    image_processing_event = threading.Event()

    # Start stream
    drone.streamon()
    thread_video_stream = start_thread_video_stream(drone, exit_event)

    # Init processing thread list
    thread_image_processing_list = []

    # Start control loop
    print("All systems online.")
    print("Use W, A, S, D for movement; R/F to move up/down; Q/E to rotate; T to takeoff; L to land; ESC to quit.")
    try:
        while True:
            key = cv2.waitKey(1) & 0xff
            if key == 27:  # ESC key
                print("Exiting program.")
                break
            elif key == ord('w'):
                drone.move_forward(5)
            elif key == ord('s'):
                drone.move_back(5)
            elif key == ord('a'):
                drone.move_left(5)
            elif key == ord('d'):
                drone.move_right(5)
            elif key == ord('e'):
                drone.rotate_clockwise(5)
            elif key == ord('q'):
                drone.rotate_counter_clockwise(5)
            elif key == ord('r'):
                drone.move_up(5)
            elif key == ord('f'):
                drone.move_down(5)
            elif key == ord('t'):
                drone.takeoff()
            elif key == ord('l'):
                drone.land()
            elif key == ord(' '):
                if not image_processing_event.is_set():
                    image_processing_event.set()
                    new_thread_image_processing = start_thread_image_processing(drone, image_stitcher, image_processing_event, exit_event)
                    thread_image_processing_list.append(new_thread_image_processing)
                else:
                    image_processing_event.clear()
            time.sleep(0.05)  # Small delay for stability

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Land the drone before exit
        if drone.is_flying:
            print("Landing the drone...")
            drone.land()

        # End threads
        exit_event.set()

        # Wait for processing threads to finish
        for thread in thread_image_processing_list:
            thread.join(timeout=5)

        # Wait for video thread to finish
        thread_video_stream.join(timeout=5)

        # Turn off stream
        drone.streamoff()

        # End connection
        drone.end()
        print("All systems offline.")


if __name__ == "__name__":
    main()
