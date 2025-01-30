import cv2
import threading
import time
import os
import pygame
import matplotlib.pyplot as plt
from djitellopy import Tello
from IPython.display import clear_output, display
from queue import Queue
from postprocessing import load_and_stitch


# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((960, 720))
pygame.display.set_caption('Tello Drone')


def get_current_output_folder_id(base_folder):
    """Returns the current output folder number (the recording ID)."""
    existing_subfolders = [f for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f))]
    numbers = [int(name) for name in existing_subfolders if name.isdigit()]
    return max(numbers, default=-1)


def add_output_folder(base_folder):
    """Creates new folder for output recordings."""
    current_folder_id = get_current_output_folder_id(base_folder)
    new_folder_id = current_folder_id + 1
    new_folder_path = os.path.join(base_folder, str(new_folder_id))
    os.makedirs(new_folder_path)
    return new_folder_path


def process_video(drone, frame_queue, exit_event):
    """Threaded function to get the video frame from the Tello drone."""
    while not exit_event.is_set():
        frame = drone.get_frame_read().frame
        if frame is not None:
            # Pass frame to main thread via queue
            frame_queue.put(frame)
        time.sleep(0.03)


def custom_rotate_clockwise(drone, rotation_speed, angle, error_correction=2):
    """Clockwise rotation with custom speed setting. Error correction is needed to get close to the given angle."""
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
    """Executes list of drone commands in separate thread."""
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
    """Perform exit procedure."""
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


def ask_user(question):
    """Asks the user a yes or now question."""
    while True:
        answer = input(f"{question} [Y/n]: ").strip().lower()
        if answer in ["yes", "y", ""]:
            return True
        elif answer in ["no", "n"]:
            return False
        else:
            print("Invalid input.")


def perform_image_stitching(input_images_dir):
    """Stitch the images located in the given directory and save the results in a subfolder."""
    output_dir = os.path.join(input_images_dir, "stitching_results")
    success = load_and_stitch(input_images_dir, output_dir)
    return success


def main(image_output_base_dir=os.path.join(".", "output_images")):
    # Initialize the Tello drone
    drone = Tello()
    drone.connect()

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

    # Recording
    initial_recording_id = get_current_output_folder_id(image_output_base_dir)
    last_saved_time = 0

    # Exit marker
    quit = False

    # Start drone control
    print("Tello Drone Control")
    print("Use W, A, S, D for movement; Shift/Ctrl to move up/down; Q/E to rotate; T to takeoff; L to land; R to record; ESC to quit.")
    print("Press 1 to perform a 360 degree panorama shot.")
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
                            add_output_folder(image_output_base_dir)
                            recording_event.set()
                        else:
                            print(f"End recording")
                            recording_event.clear()
                    elif event.key == pygame.K_1:
                        print("Initiate panorama recording...")
                        commands_list = [
                            (add_output_folder, image_output_base_dir),
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
                    if time_diff >= 1:
                        frame_output = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        timestamp = str(int(time.time()*1000.0))
                        current_folder_id = get_current_output_folder_id(image_output_base_dir)
                        image_path = os.path.join(image_output_base_dir, str(current_folder_id), f"frame_{timestamp}.png")
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

        # Close camera window
        pygame.quit()

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
        try:
            drone.streamoff()
        except Exception as e:
            print(e)


        # End connection
        drone.end()
        print("All systems offline.")

        # Postprocessing
        current_recording_id = get_current_output_folder_id(image_output_base_dir)
        if initial_recording_id != current_recording_id:
            do_stitching = ask_user("Start stitching process now?")
            if not do_stitching:
                return
            for i in range(initial_recording_id, current_recording_id):
                recording_id = i+1
                print(f"Working on recording {recording_id}")
                input_images_dir = os.path.join(image_output_base_dir, str(recording_id))
                success = perform_image_stitching(input_images_dir)
                if success:
                    print("Stitching process complete.")
                else:
                    print("Stitching process failed.")


if __name__ == "__main__":
    main()
