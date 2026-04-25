# pyright: reportOptionalMemberAccess=false

# Exit codes: 0 = success (user quit), 1 = camera unavailable, 2 = cascade download failed

import functools
import os
import sys

import cv2
import requests

print = functools.partial(print, flush=True)


def download_haarcascade(filename):
    url = f"https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/{filename}"
    print("STATUS: cascade_downloading")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"cascade download failed: {e}", file=sys.stderr)
        print("STATUS: cascade_download_failed")
        sys.exit(2)
    with open(filename, "wb") as f:
        f.write(response.content)


def capture_and_grayscale():
    filename = "haarcascade_frontalface_default.xml"

    if not os.path.isfile(filename):
        print(f"{filename} not found, downloading...", file=sys.stderr)
        download_haarcascade(filename)

    face_cascade = cv2.CascadeClassifier(filename)

    print("STATUS: requesting_camera")
    working_cam = None
    any_opened = False
    for index in range(3):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            any_opened = True
            ret, _ = cap.read()
            if ret:
                working_cam = cap
                break
        cap.release()

    if working_cam is None:
        if any_opened:
            print("camera opened but frames could not be read (permission denied?)", file=sys.stderr)
        else:
            print("no camera found at indices 0-2", file=sys.stderr)
        print("STATUS: camera_denied_or_unavailable")
        sys.exit(1)

    print("STATUS: camera_ready")
    print("STATUS: capture_started")

    while True:
        ret, frame = working_cam.read()

        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        for x, y, w, h in faces:
            gray_bgr[y : y + h, x : x + w] = frame[y : y + h, x : x + w]
            cv2.rectangle(gray_bgr, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.imshow("Input", gray_bgr)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    working_cam.release()
    cv2.destroyAllWindows()
    print("STATUS: capture_stopped")


if __name__ == "__main__":
    capture_and_grayscale()
