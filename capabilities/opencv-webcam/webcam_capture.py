# pyright: reportOptionalMemberAccess=false

import os

import cv2
import requests


def download_haarcascade(filename):
    url = f"https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/{filename}"
    response = requests.get(url)
    response.raise_for_status()
    with open(filename, "wb") as f:
        f.write(response.content)


def capture_and_grayscale():
    filename = "haarcascade_frontalface_default.xml"

    if not os.path.isfile(filename):
        print(f"{filename} not found, downloading...")
        download_haarcascade(filename)

    face_cascade = cv2.CascadeClassifier(filename)

    working_cam = None
    for index in range(3):
        cap = cv2.VideoCapture(index)
        if not cap.read()[0]:
            cap.release()
            continue

        working_cam = cap
        break

    if not working_cam or not working_cam.isOpened():
        raise OSError("Cannot open webcam")

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


if __name__ == "__main__":
    capture_and_grayscale()
