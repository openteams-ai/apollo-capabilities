# OpenCV Webcam

A capability based on the Pixi OpenCV example (webcam capture only).

This capability supports local execution only because it requires webcam and display access.

## What it does

- Opens an available webcam
- Converts each frame to grayscale
- Detects faces with a Haar cascade
- Keeps detected face regions in color

Press `q` to quit.

## Usage

```sh
pixi run launch
```

## Status protocol

The script writes `STATUS: <value>` lines to **stdout** at key lifecycle points. Error details go to **stderr**. Consumers (e.g. the Wails host app) should parse stdout for these tokens.

| Status value | Meaning |
|---|---|
| `STATUS: requesting_camera` | About to attempt `cv2.VideoCapture` on available indices |
| `STATUS: camera_ready` | A camera was opened and the first frame read successfully |
| `STATUS: camera_denied_or_unavailable` | No usable camera found; check stderr for detail (no device vs. permission denied) |
| `STATUS: cascade_downloading` | Haar cascade XML not found locally; download starting |
| `STATUS: cascade_download_failed` | Download failed; check stderr for detail |
| `STATUS: capture_started` | Entering the main capture loop; window is about to appear |
| `STATUS: capture_stopped` | Main loop exited cleanly (user pressed `q` or frame read failed) |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — user quit normally |
| `1` | Camera unavailable (not found or permission denied) |
| `2` | Haar cascade download failed |
