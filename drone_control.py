import cv2
import threading
import time
import pygame
import matplotlib.pyplot as plt
from djitellopy import Tello
from IPython.display import clear_output, display
from stitching import Stitcher


# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((960, 720))
pygame.display.set_caption('Tello Drone')


def display_video_frame(drone, exit_event):
    while not exit_event.is_set():
        # Capture frame from the drone
        frame = drone.get_frame_read().frame

        # Convert frame a format compatible with pygame (RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.surfarray.make_surface(frame_rgb)
        frame_surface = pygame.transform.rotate(frame_surface, -90)  # Rotate for correct orientation
        frame_surface = pygame.transform.flip(frame_surface, True, False)  # Flip horizontally if needed

        # Display frame in Pygame window
        screen.blit(frame_surface, (0, 0))
        pygame.display.update()

        # Reduce CPU usage
        time.sleep(0.03)


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
    #drone = Tello()
    #drone.connect()
    #print(f"Battery level: {drone.get_battery()}%")

    # Initialize image stitching tool
    image_stitcher = Stitcher(confidence_threshold=0.1)

    # Set events
    exit_event = threading.Event()
    image_processing_event = threading.Event()

    # Start stream
    #drone.streamon()
    #thread_video_stream = threading.Thread(target=display_video_frame, args=(drone, exit_event))
    #thread_video_stream.start()

    # Init processing thread list
    thread_image_processing_list = []

    # Start control loop
    print("Tello Drone Control")
    print("Use W, A, S, D for movement; R/F to move up/down; Q/E to rotate; T to takeoff; L to land; ESC to quit.")
    print("All systems online.")
    try:
        # Control loop
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    exit_event.set()
                    break

                # Handle key press events
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_w:
                        print("Moving forward")
                        #drone.move_forward(20)
                    elif event.key == pygame.K_s:
                        print("Moving back")
                        #drone.move_back(20)
                    elif event.key == pygame.K_a:
                        print("Moving left")
                        #drone.move_left(20)
                    elif event.key == pygame.K_d:
                        print("Moving right")
                        #drone.move_right(20)
                    elif event.key == pygame.K_q:
                        print("Rotating counterclockwise")
                        #drone.rotate_counter_clockwise(20)
                    elif event.key == pygame.K_e:
                        print("Rotating clockwise")
                        #drone.rotate_clockwise(20)
                    elif event.key == pygame.K_r:
                        print("Moving up")
                        #drone.move_up(20)
                    elif event.key == pygame.K_f:
                        print("Moving down")
                        #drone.move_down(20)
                    elif event.key == pygame.K_t:
                        print("Takeoff")
                        #drone.takeoff()
                    elif event.key == pygame.K_l:
                        print("Landing")
                        #drone.land()
                    elif event.key == pygame.K_c:
                        if not image_processing_event.is_set():
                            image_processing_event.set()
                            print("Start recording.")
                            #new_thread_image_processing = start_thread_image_processing(drone, image_stitcher, image_processing_event, exit_event)
                            #thread_image_processing_list.append(new_thread_image_processing)
                        else:
                            print("End recording.")
                            image_processing_event.clear()
                    elif event.key == pygame.K_ESCAPE:
                        print("Exiting program.")
                        exit_event.set()
                        break

            # Break the loop if exit event is set
            if exit_event.is_set():
                break

            time.sleep(0.1)  # Small delay for stability

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Land the drone before exit
        #if drone.is_flying:
        #    print("Landing the drone...")
        #drone.land()

        # End threads
        exit_event.set()

        # Wait for processing threads to finish
        for thread in thread_image_processing_list:
            thread.join(timeout=5)

        # Wait for video thread to finish
        #thread_video_stream.join(timeout=5)

        # Turn off stream
        #drone.streamoff()

        # End connection
        #drone.end()
        print("All systems offline.")


if __name__ == "__main__":
    main()
