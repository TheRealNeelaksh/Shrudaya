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

try:
    from absl import logging as absl_logging
    absl_logging.set_verbosity(absl_logging.FATAL)
    absl_logging._warn_preinit_stderr = False
    absl_logging.get_absl_handler().use_absl_log_file()
    absl_logging.get_absl_handler().set_log_file(os.path.splitext(log_file)[0])
except Exception as e:
    print(f"Could not configure absl logging: {e}")

import cv2
import mediapipe as mp
import numpy as np
import random
import time

# Optional: Disable QT usage for headless/server usage (if needed)
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

def animate_face_during_conversation():
    # Load VED's face images
    ved_eyes_open = cv2.imread('face/faces_data/baymax/bmax_eyesopen.png')
    ved_eyes_closed = cv2.imread('face/faces_data/baymax/bmax_eyesclose.png')

    # Resize the eye images
    eyes_height, eyes_width, _ = ved_eyes_open.shape
    resize_factor = 1.5  # enlarge eyes
    ved_eyes_open = cv2.resize(ved_eyes_open, (int(eyes_width * resize_factor), int(eyes_height * resize_factor)))
    ved_eyes_closed = cv2.resize(ved_eyes_closed, (int(eyes_width * resize_factor), int(eyes_height * resize_factor)))

    eyes_height, eyes_width, _ = ved_eyes_open.shape

    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils

    def is_blinking(landmarks, h, w):
        left_eye_top = (int(landmarks[159].x * w), int(landmarks[159].y * h))
        left_eye_bottom = (int(landmarks[145].x * w), int(landmarks[145].y * h))
        left_eye_height = np.linalg.norm(np.array(left_eye_top) - np.array(left_eye_bottom))

        right_eye_top = (int(landmarks[386].x * w), int(landmarks[386].y * h))
        right_eye_bottom = (int(landmarks[374].x * w), int(landmarks[374].y * h))
        right_eye_height = np.linalg.norm(np.array(right_eye_top) - np.array(right_eye_bottom))

        # Threshold for blink detection
        return left_eye_height < 5 or right_eye_height < 5

    def update_ved_eyes(center_x, center_y, blinking, current_pos, smoothing_factor=0.4):
        display_image = np.ones((720, 1280, 3), dtype=np.uint8) * 255

        max_offset_x = int(display_image.shape[1] * 0.2)
        max_offset_y = int(display_image.shape[0] * 0.2)

        target_x = int(display_image.shape[1] // 2 + (center_x - display_image.shape[1] // 2) * 0.1)
        target_y = int(display_image.shape[0] // 2 + (center_y - display_image.shape[0] // 2) * 0.1)

        current_pos[0] = int(current_pos[0] + (target_x - current_pos[0]) * smoothing_factor)
        current_pos[1] = int(current_pos[1] + (target_y - current_pos[1]) * smoothing_factor)

        top_left_x = max(0, min(current_pos[0] - eyes_width // 2, display_image.shape[1] - eyes_width))
        top_left_y = max(0, min(current_pos[1] - eyes_height // 2, display_image.shape[0] - eyes_height))

        eyes_image = ved_eyes_closed if blinking else ved_eyes_open

        display_image[top_left_y:top_left_y + eyes_height, top_left_x:top_left_x + eyes_width] = eyes_image

        cv2.imshow(window_name, display_image)

    # For random blinking simulation timing
    def random_blink_timer():
        # Returns next blink delay in seconds (~3-7s)
        return random.uniform(3.0, 7.0)

    window_name = 'Project VED - Face'
    cv2.namedWindow(window_name)

    cap = cv2.VideoCapture(0)
    current_pos = [640, 360]

    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5) as face_mesh:

        blink_state = False          # Are we currently blinking?
        blink_duration_frames = 3    # How many frames to keep eyes closed during a blink
        blink_frame_counter = 0

        last_blink_time = time.time()
        next_blink_delay = random_blink_timer()

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)

            face_center_x = 640
            face_center_y = 360
            user_blinking = False

            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    mp_drawing.draw_landmarks(frame, face_landmarks)

                    h, w, _ = frame.shape
                    landmarks = face_landmarks.landmark
                    face_center_x = int((landmarks[33].x + landmarks[263].x) / 2 * w)
                    face_center_y = int((landmarks[33].y + landmarks[263].y) / 2 * h)

                    user_blinking = is_blinking(landmarks, h, w)

            # Simulate blink randomly if user is NOT blinking
            current_time = time.time()

            if user_blinking:
                blink_state = True
                blink_frame_counter = blink_duration_frames
                last_blink_time = current_time
                next_blink_delay = random_blink_timer()
            else:
                if blink_frame_counter > 0:
                    blink_frame_counter -= 1
                    blink_state = True
                else:
                    # If time for next random blink
                    if current_time - last_blink_time > next_blink_delay:
                        blink_state = True
                        blink_frame_counter = blink_duration_frames
                        last_blink_time = current_time
                        next_blink_delay = random_blink_timer()
                    else:
                        blink_state = False

            update_ved_eyes(face_center_x, face_center_y, blink_state, current_pos)

            cv2.imshow('Face Mesh Detection', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    animate_face_during_conversation()
    