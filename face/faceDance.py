import os
import sys
import logging
from datetime import datetime

# === STEP 1: Set environment variables to suppress logs in terminal ===
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"
os.environ["ABSL_LOG_TO_STDERR"] = "0"

# === STEP 2: Setup logging to a file (overwrite every run) ===
log_file = "ved_log.txt"
log_path = os.path.abspath(log_file)

# Clear the log file and add session start header
with open(log_file, 'w') as f:
    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] New session started\n")

# Configure basic logging to file using Python's standard logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_file,
    filemode='a' # Append to the log file
)

try:
    from absl import logging as absl_logging
    # Suppress absl logging messages to fatal level.
    # This prevents absl's own messages from appearing in stderr.
    absl_logging.set_verbosity(absl_logging.FATAL)
    # The previous lines related to absl file logging (e.g., use_absl_log_file, set_log_file)
    # have been removed as they were causing the AttributeError.
    # Standard Python logging is used for file output (ved_log.txt).
except Exception as e:
    logging.error(f"Could not configure absl logging: {e}")
    print(f"Could not configure absl logging: {e}") # Also print to console for immediate feedback

import cv2
import mediapipe as mp
import numpy as np
import random
import time

# Optional: Disable QT usage for headless/server usage (if needed)
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

def animate_face_during_conversation():
    # Define image paths
    eyes_open_path = 'face/faces_data/baymax/bmax_eyesopen.png'
    eyes_closed_path = 'face/faces_data/baymax/bmax_eyesclose.png'

    # Load VED's face images
    ved_eyes_open = cv2.imread(eyes_open_path)
    ved_eyes_closed = cv2.imread(eyes_closed_path)

    # --- ERROR HANDLING: Check if images were loaded successfully ---
    if ved_eyes_open is None:
        logging.error(f"Error: Could not load image from {eyes_open_path}. Please check the path and file existence.")
        print(f"Error: Could not load image from {eyes_open_path}. Please check the path and file existence.")
        # Fallback: Create a simple placeholder image if the actual image is not found
        # This allows the script to continue running for demonstration purposes
        placeholder_size = (200, 100) # width, height
        ved_eyes_open = np.zeros((placeholder_size[1], placeholder_size[0], 3), dtype=np.uint8)
        cv2.ellipse(ved_eyes_open, (placeholder_size[0]//4, placeholder_size[1]//2), (20, 30), 0, 0, 360, (0, 0, 255), -1) # Left eye
        cv2.ellipse(ved_eyes_open, (3*placeholder_size[0]//4, placeholder_size[1]//2), (20, 30), 0, 0, 360, (0, 0, 255), -1) # Right eye
        cv2.putText(ved_eyes_open, "Eyes Open", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        logging.info("Using placeholder image for eyes open.")

    if ved_eyes_closed is None:
        logging.error(f"Error: Could not load image from {eyes_closed_path}. Please check the path and file existence.")
        print(f"Error: Could not load image from {eyes_closed_path}. Please check the path and file existence.")
        # Fallback: Create a simple placeholder image for closed eyes
        placeholder_size = (200, 100) # width, height
        ved_eyes_closed = np.zeros((placeholder_size[1], placeholder_size[0], 3), dtype=np.uint8)
        cv2.line(ved_eyes_closed, (placeholder_size[0]//4 - 25, placeholder_size[1]//2), (placeholder_size[0]//4 + 25, placeholder_size[1]//2), (0, 0, 255), 5) # Left eye line
        cv2.line(ved_eyes_closed, (3*placeholder_size[0]//4 - 25, placeholder_size[1]//2), (3*placeholder_size[0]//4 + 25, placeholder_size[1]//2), (0, 0, 255), 5) # Right eye line
        cv2.putText(ved_eyes_closed, "Eyes Closed", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        logging.info("Using placeholder image for eyes closed.")

    # Resize the eye images
    eyes_height, eyes_width, _ = ved_eyes_open.shape
    resize_factor = 1.5  # enlarge eyes
    ved_eyes_open = cv2.resize(ved_eyes_open, (int(eyes_width * resize_factor), int(eyes_height * resize_factor)))
    ved_eyes_closed = cv2.resize(ved_eyes_closed, (int(eyes_width * resize_factor), int(eyes_height * resize_factor)))

    eyes_height, eyes_width, _ = ved_eyes_open.shape # Recalculate after resizing

    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils

    def is_blinking(landmarks, h, w, blink_threshold=5):
        """
        Determines if the eyes are blinking based on eye landmark vertical distance.
        A lower distance indicates a closed eye.
        """
        # Left eye landmarks for top and bottom
        left_eye_top = (int(landmarks[159].x * w), int(landmarks[159].y * h))
        left_eye_bottom = (int(landmarks[145].x * w), int(landmarks[145].y * h))
        left_eye_height = np.linalg.norm(np.array(left_eye_top) - np.array(left_eye_bottom))

        # Right eye landmarks for top and bottom
        right_eye_top = (int(landmarks[386].x * w), int(landmarks[386].y * h))
        right_eye_bottom = (int(landmarks[374].x * w), int(landmarks[374].y * h))
        right_eye_height = np.linalg.norm(np.array(right_eye_top) - np.array(right_eye_bottom))

        # Threshold for blink detection
        return left_eye_height < blink_threshold or right_eye_height < blink_threshold

    def update_ved_eyes(center_x, center_y, blinking, current_pos, smoothing_factor=0.4):
        """
        Updates the display window with the VED face, moving eyes based on user's face position
        and showing open/closed eyes based on blinking state.
        """
        # Create a white background image for display
        display_image = np.ones((720, 1280, 3), dtype=np.uint8) * 255

        # Calculate target position for VED's eyes based on user's face center
        # The 0.1 factor makes VED's eyes move less dramatically than the user's head
        target_x = int(display_image.shape[1] // 2 + (center_x - display_image.shape[1] // 2) * 0.1)
        target_y = int(display_image.shape[0] // 2 + (center_y - display_image.shape[0] // 2) * 0.1)

        # Smoothly interpolate current position towards the target position
        current_pos[0] = int(current_pos[0] + (target_x - current_pos[0]) * smoothing_factor)
        current_pos[1] = int(current_pos[1] + (target_y - current_pos[1]) * smoothing_factor)

        # Ensure the eyes stay within the display boundaries
        top_left_x = max(0, min(current_pos[0] - eyes_width // 2, display_image.shape[1] - eyes_width))
        top_left_y = max(0, min(current_pos[1] - eyes_height // 2, display_image.shape[0] - eyes_height))

        # Select the appropriate eye image (open or closed)
        eyes_image = ved_eyes_closed if blinking else ved_eyes_open

        # Overlay the eyes image onto the display image
        display_image[top_left_y:top_left_y + eyes_height, top_left_x:top_left_x + eyes_width] = eyes_image

        # Show the updated display
        cv2.imshow(window_name, display_image)

    def random_blink_timer():
        """
        Returns the delay in seconds until the next simulated blink.
        """
        return random.uniform(3.0, 7.0) # Random delay between 3 and 7 seconds

    window_name = 'Project VED - Face'
    cv2.namedWindow(window_name)

    cap = cv2.VideoCapture(0) # Initialize video capture from default camera
    if not cap.isOpened():
        logging.error("Error: Could not open video stream. Check if camera is available and not in use.")
        print("Error: Could not open video stream. Check if camera is available and not in use.")
        return # Exit if camera cannot be opened

    current_pos = [640, 360] # Initial center position for VED's eyes

    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5) as face_mesh:

        blink_state = False          # Is VED currently blinking?
        blink_duration_frames = 3    # How many frames to keep VED's eyes closed during a simulated blink
        blink_frame_counter = 0      # Counter for simulated blink frames

        last_blink_time = time.time() # Timestamp of the last blink (user or simulated)
        next_blink_delay = random_blink_timer() # Time until the next simulated blink

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                logging.warning("Ignoring empty camera frame.")
                # If the camera is disconnected or not providing frames, try to re-open
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    print("Failed to re-open camera. Exiting.")
                    break
                continue

            # Flip the frame horizontally for a mirror effect, common for webcam feeds
            frame = cv2.flip(frame, 1)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Process the frame to find face landmarks
            results = face_mesh.process(rgb_frame)

            face_center_x = frame.shape[1] // 2 # Default to center if no face detected
            face_center_y = frame.shape[0] // 2 # Default to center if no face detected
            user_blinking = False

            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    # Optionally draw face mesh landmarks on the user's camera feed
                    # mp_drawing.draw_landmarks(frame, face_landmarks, mp_face_mesh.FACEMESH_CONTOURS,
                    #                           mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1),
                    #                           mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=1, circle_radius=1))

                    h, w, _ = frame.shape
                    landmarks = face_landmarks.landmark
                    # Calculate approximate center of the detected face
                    face_center_x = int((landmarks[33].x + landmarks[263].x) / 2 * w) # Left and Right eye outer corners
                    face_center_y = int((landmarks[33].y + landmarks[263].y) / 2 * h)

                    user_blinking = is_blinking(landmarks, h, w)

            # --- Blink Logic: Prioritize user blink, then simulate random blink ---
            current_time = time.time()

            if user_blinking:
                # If user is blinking, force VED to blink
                blink_state = True
                blink_frame_counter = blink_duration_frames
                last_blink_time = current_time # Reset random blink timer
                next_blink_delay = random_blink_timer() # Get new random delay
            else:
                if blink_frame_counter > 0:
                    # If VED is in the middle of a simulated blink, continue it
                    blink_frame_counter -= 1
                    blink_state = True
                else:
                    # If VED is not blinking and not in a simulated blink, check for random blink trigger
                    if current_time - last_blink_time > next_blink_delay:
                        blink_state = True
                        blink_frame_counter = blink_duration_frames
                        last_blink_time = current_time
                        next_blink_delay = random_blink_timer()
                    else:
                        blink_state = False # VED's eyes are open

            # Update and display VED's eyes
            update_ved_eyes(face_center_x, face_center_y, blink_state, current_pos)

            # Display the user's camera feed (optional, for debugging/visualization)
            cv2.imshow('Face Mesh Detection', frame)

            # Exit on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release() # Release the camera
    cv2.destroyAllWindows() # Close all OpenCV windows


if __name__ == "__main__":
    animate_face_during_conversation()
