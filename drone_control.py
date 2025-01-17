import cv2
import threading
import time
import os
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


def process_video(drone, frame_queue, exit_event):
    """Threaded function to capture the video frame from the Tello drone."""
    while not exit_event.is_set():
        frame = drone.get_frame_read().frame
        if frame is not None:
            # Pass frame to main thread via queue
            frame_queue.put(frame)
        time.sleep(0.03)


def custom_rotate_clockwise(drone, rotation_speed, angle, error_correction=2):
    """Clockwise rotation with custom speed setting. Error correction can be used to get closer to the given angle."""
    duration = (angle / rotation_speed) * error_correction
    drone.send_rc_control(0, 0, 0, rotation_speed)
    time.sleep(duration)
    drone.send_rc_control(0, 0, 0, 0)


def set_recording_event(recording_event, value=True):
    """Sets or clears the recording event."""
    if value:
        recording_event.set()
    else:
        recording_event.clear()


def set_exit_event(exit_event):
    """Set the exit event."""
    exit_event.set()


def execute_commands_in_thread(commands_list, command_event, exit_event=None):
    """Executes a list of drone command in a separate thread."""
    command_event.set()
    def target():
        try:
            for command in commands_list:
                if exit_event and exit_event.is_set():
                    print("Stopping early.")
                    break
                func, *args = command
                name = func.__name__
                print(f'Waiting for: "{name}"')
                time.sleep(0.1)
                func(*args)
                time.sleep(0.1)
                print(f'"{name}" done')
        except Exception as e:
            print(f'Error executing command "{name}": {e}')
        finally:
            command_event.clear()
    thread = threading.Thread(target=target)
    thread.start()


def takeoff_check(drone):
    """Perform a takeoff check and return result."""
    takeoff_okay = True

    # Check if drone is flying
    if drone.is_flying:
        takeoff_okay = False

    # Check battery level
    battery_level = drone.get_battery()
    if battery_level < 5:
        print(f"Please charge. Battery too low for takeoff: {battery_level}%")
        takeoff_okay = False

    return takeoff_okay


def do_landing(drone, command_event):
    """Perform a landing."""
    if drone.is_flying:
        print("Landing")
        execute_commands_in_thread([(drone.land,)], command_event)


def prepare_exit(drone, command_event, recording_event, exit_event):
    """Prepare for exiting the program."""
    recording_event.clear()
    if exit_event.is_set():
        return
    if command_event.is_set():
        print("Abort.")
        exit_event.set()
    else:
        print("Exiting program...")
        if drone.is_flying:
            execute_commands_in_thread([(drone.land,), (set_exit_event, exit_event)], command_event)
        else:
            exit_event.set()


def main():
    # Initialize the Tello drone
    drone = Tello()
    drone.connect()

    # Initialize image stitching tool
    image_output_dir = "./output_images"

    # Set events
    command_event = threading.Event()
    recording_event = threading.Event()
    exit_event = threading.Event()

    # Start stream
    drone.streamon()

    # Thread-safe queue for video frames
    frame_queue = Queue(maxsize=1)

    # Start video stream thread
    thread_video_stream = threading.Thread(target=process_video, args=(drone, frame_queue, exit_event))
    thread_video_stream.start()

    # Init processing thread list
    #thread_image_processing_list = []

    # Movement variables
    movement_speed = 30
    rotation_speed = 30
    forward = 0
    left = 0
    up = 0
    yaw = 0
    last_command = (0, 0, 0, 0)

    # Timer
    clock = pygame.time.Clock()

    # Recording variables
    recording_id = 0
    last_saved_time = 0

    # Exit marker
    quit = False

    # Start drone control
    print("Tello Drone Control")
    print("Use W, A, S, D for movement; Shift/Ctrl to move up/down; Q/E to rotate; T to takeoff; L to land; R to record; ESC to quit.")
    print("All systems online.")
    print(f"Battery level: {drone.get_battery()}%")
    try:
        # Main control loop
        while True:
            # Exit condition
            if exit_event.is_set():
                print("Quit")
                break

            # Capture pygame events
            for event in pygame.event.get():
                # Handle quit event
                if event.type == pygame.QUIT and not quit:
                    prepare_exit(drone, command_event, recording_event, exit_event)
                    quit = True

                # Handle key press events
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE and not quit:
                        prepare_exit(drone, command_event, recording_event, exit_event)
                        quit = True
                    elif command_event.is_set():
                        break
                    elif event.key == pygame.K_w:
                        print("Moving forward")
                        forward = 1
                    elif event.key == pygame.K_s:
                        print("Moving back")
                        forward = -1
                    elif event.key == pygame.K_a:
                        print("Moving left")
                        left = -1
                    elif event.key == pygame.K_d:
                        print("Moving right")
                        left = 1
                    elif event.key == pygame.K_LSHIFT:
                        print("Moving up")
                        up = 1
                    elif event.key == pygame.K_LCTRL:
                        print("Moving down")
                        up = -1
                    elif event.key == pygame.K_q:
                        print("Rotating counterclockwise")
                        yaw = -1
                    elif event.key == pygame.K_e:
                        print("Rotating clockwise")
                        yaw = 1
                    elif event.key == pygame.K_PLUS and movement_speed < 50:
                        movement_speed += 10
                        rotation_speed += 5
                        print(f"Set speed: {movement_speed}")
                    elif event.key == pygame.K_MINUS and movement_speed > 10:
                        movement_speed -= 10
                        rotation_speed -= 5
                        print(f"Set speed: {movement_speed}")
                    elif event.key == pygame.K_t and takeoff_check(drone):
                        print("Takeoff")
                        execute_commands_in_thread([(drone.takeoff,)], command_event)
                    elif event.key == pygame.K_l:
                        do_landing(drone, command_event)
                    elif event.key == pygame.K_r:
                        if not recording_event.is_set():
                            print(f"Start recording")
                            recording_event.set()
                        else:
                            print(f"End recording")
                            recording_event.clear()
                    elif event.key == pygame.K_1:
                        print("Initiate panorama recording...")
                        commands_list = [
                            (set_recording_event, recording_event),
                            *((custom_rotate_clockwise, drone, rotation_speed, 90),)*4,
                            (set_recording_event, recording_event, False)]
                        if takeoff_check(drone):
                            commands_list = [
                                (drone.takeoff,),
                                (drone.move_up, 100),
                                *commands_list,
                                (drone.land,),
                                (set_exit_event, exit_event)]
                        execute_commands_in_thread(commands_list, command_event, exit_event)

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

            # Pause manual controls
            if command_event.is_set():
                forward = left = up = yaw = 0

            # Send control commands
            current_command = (left * movement_speed, forward * movement_speed, up * movement_speed, yaw * rotation_speed)
            if current_command != last_command:
                drone.send_rc_control(*current_command)
                last_command = current_command

            # Handle video frames
            if not frame_queue.empty():
                frame = frame_queue.get()
                frame = cv2.flip(frame, 1)
                frame_surface = pygame.surfarray.make_surface(frame)
                frame_surface = pygame.transform.rotate(frame_surface, -90)
                frame_surface = pygame.transform.scale(frame_surface, screen.get_size())
                screen.blit(frame_surface, (0, 0))
                pygame.display.update()

                # Save to png
                if recording_event.is_set():
                    current_time = time.time()
                    time_diff = current_time - last_saved_time
                    if time_diff >= 2:
                        recording_id += 1
                    if time_diff >= 0.5:
                        frame_output = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        image_path = os.path.join(image_output_dir, f"frame_{timestamp}.png")
                        cv2.imwrite(image_path, frame_output)
                        print(f"Saved: {image_path}")
                        last_saved_time = current_time

            # Cap the loop rate
            clock.tick(60)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Exit signal
        if not exit_event.is_set():
            exit_event.set()

        # Wait for the drone
        print("Waiting for drone to finish...")
        while command_event.is_set():
            time.sleep(0.5)
        time.sleep(2)

        # Land the drone
        do_landing(drone, command_event)

        # Wait for video thread to finish
        thread_video_stream.join(timeout=5)

        # Turn off stream
        drone.streamoff()

        # End connection
        drone.end()
        print("All systems offline.")


if __name__ == "__main__":
    main()
