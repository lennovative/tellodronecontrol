import cv2
import threading
import time
import pygame
import matplotlib.pyplot as plt
from djitellopy import Tello
from IPython.display import clear_output, display
from stitching import Stitcher
from queue import Queue


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


def display_video_frame(drone, frame_queue, exit_event):
    """Threaded function to capture the video frame from the Tello drone."""
    while not exit_event.is_set():
        frame = drone.get_frame_read().frame
        if frame is not None:
            # Pass frame to main thread via queue
            frame_queue.put(frame)
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


def do_takeoff(drone):
    print("Takeoff")
    try:
        response = drone.send_control_command("takeoff")
        if response:
            print("Takeoff successful")
    except Exception as e:
        print(f"Error during takeoff: {e}")


def do_landing(drone):
    print("Landing")
    try:
        response = drone.land()
        if response:
            print("Landing successful")
    except Exception as e:
        print(f"Error during landing: {e}")


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

    # Thread-safe queue for video frames
    frame_queue = Queue(maxsize=1)

    # Start video stream thread
    thread_video_stream = threading.Thread(target=display_video_frame, args=(drone, frame_queue, exit_event))
    thread_video_stream.start()

    # Init processing thread list
    thread_image_processing_list = []

    # Start drone control
    print("Tello Drone Control")
    print("Use W, A, S, D for movement; R/F to move up/down; Q/E to rotate; T to takeoff; L to land; ESC to quit.")
    # Initialize movement variables
    forward = 0
    left = 0
    up = 0
    yaw = 0
    last_command = (0, 0, 0, 0)
    rc_control_active = False
    clock = pygame.time.Clock()
    print("All systems online.")
    try:
        # Main control loop
        while True:
            # Capture events
            for event in pygame.event.get():
                # Handle quit event
                if event.type == pygame.QUIT:
                    print("Exiting program.")
                    exit_event.set()
                    break

                # Handle key press events
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_w:
                        print("Moving forward")
                        forward = 30
                    elif event.key == pygame.K_s:
                        print("Moving back")
                        forward = -30
                    elif event.key == pygame.K_a:
                        print("Moving left")
                        left = -30
                    elif event.key == pygame.K_d:
                        print("Moving right")
                        left = 30
                    elif event.key == pygame.K_LSHIFT:
                        print("Moving up")
                        up = 30
                    elif event.key == pygame.K_LCTRL:
                        print("Moving down")
                        up = -30
                    elif event.key == pygame.K_q:
                        print("Rotating counterclockwise")
                        yaw = -60
                    elif event.key == pygame.K_e:
                        print("Rotating clockwise")
                        yaw = 60
                    elif event.key == pygame.K_t and not drone.is_flying:
                        battery_level = drone.get_battery()
                        print(f"Battery level: {battery_level}%")
                        if battery_level < 15:
                            print("Battery too low for takeoff! Please charge.")
                        else:
                            do_takeoff(drone)
                            rc_control_active = True
                    elif event.key == pygame.K_l:
                        do_landing(drone)
                        rc_control_active = False  # Deactivate rc_control
                    elif event.key == pygame.K_r:
                        if not image_processing_event.is_set():
                            image_processing_event.set()
                            print("Start recording")
                            new_thread_image_processing = start_thread_image_processing(
                                drone, image_stitcher, image_processing_event, exit_event)
                            thread_image_processing_list.append(new_thread_image_processing)
                        else:
                            print("End recording")
                            image_processing_event.clear()
                    elif event.key == pygame.K_ESCAPE:
                        print("Exiting program.")
                        rc_control_active = False
                        exit_event.set()
                        break

                # Handle key release events
                elif event.type == pygame.KEYUP:
                    if event.key in [pygame.K_w, pygame.K_s]:
                        forward = 0
                    elif event.key in [pygame.K_a, pygame.K_d]:
                        left = 0
                    elif event.key in [pygame.K_LSHIFT, pygame.K_LCTRL]:
                        up = 0
                    elif event.key in [pygame.K_q, pygame.K_e]:
                        yaw = 0

            # Send real-time control commands if active
            current_command = (left, forward, up, yaw)
            if rc_control_active and current_command != last_command:
                drone.send_rc_control(*current_command)
                last_command = current_command

            # Handle video frame rendering
            if not frame_queue.empty():
                frame = frame_queue.get()
                frame = cv2.flip(frame, 1)
                frame_rgb = frame # cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_surface = pygame.surfarray.make_surface(frame_rgb)
                frame_surface = pygame.transform.rotate(frame_surface, -90)
                frame_surface = pygame.transform.scale(frame_surface, screen.get_size())
                screen.blit(frame_surface, (0, 0))
                pygame.display.update()

            # Break the loop if exit event is set
            if exit_event.is_set():
                break

            # Cap the loop rate
            clock.tick(60)

    except Exception as e:
        print(f"An error occurred: {e}")
        exit_event.set()

    finally:
        # Land the drone before exit
        do_landing(drone)

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


if __name__ == "__main__":
    main()
