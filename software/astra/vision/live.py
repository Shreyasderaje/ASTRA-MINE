"""Live camera perceiver for the REAL rover (runs on the Pi or the laptop).

A background thread grabs camera frames at ~2 Hz, runs the resource-marker
detector (vision.detector: HSV baseline, or YOLO if you trained one), and
converts each detection's pixel position into a GROUND point in front of the
rover. The dashboard's real-mode loop then fuses that point into the resource
belief map (ResourceMapper.fuse) - exactly the data path the simulated
'noisy observation' stands in for.

GEOMETRY (keep it simple and honest - calibrate on your testbed):
    The camera sits on a mast looking forward/down. We treat the lower part
    of the frame as the ground strip in front of the rover:
      * a detection's row in the image maps to a FORWARD distance (metres)
      * a detection's column maps to a LATERAL offset (metres)
    Two calibration constants (below) capture that mapping. Calibrate by
    placing a marker at a known distance/lateral offset and tuning until the
    dashboard cue appears on the right cell.

This is a PROXY sensor (documented as such in the report): it detects the
coloured marker pebbles that SIMULATE the resource signature, not actual
water ice. Report language: "resource-proxy estimation in a terrestrial
analogue environment".

Requires:  pip install opencv-python
"""
from __future__ import annotations

import math
import threading
import time

import numpy as np

# --- calibration constants (TUNE THESE ON THE TESTBED, see docs/06) --------
FRAME_BOTTOM_DEPTH_M = 0.45   # ground distance mapped by the bottom of frame
FRAME_TOP_DEPTH_M = 0.15      # ground distance mapped by ~60% height of frame
PX_PER_M_LATERAL = 900.0      # horizontal pixels per metre at ground level
GRAB_INTERVAL_S = 0.5         # camera cadence (2 Hz is plenty)


class MastCameraGeometry:
    """Pixel (u, v) in a camera frame -> (forward_m, lateral_m) on the ground.

    v = 0 is the TOP of the frame. Pixels below v_split are treated as ground.
    """

    def __init__(self, frame_width: int, frame_height: int,
                 v_split_frac: float = 0.55):
        self.w = frame_width
        self.h = frame_height
        self.v_split = int(v_split_frac * frame_height)

    def to_ground(self, u: float, v: float) -> tuple[float, float] | None:
        if v < self.v_split:          # sky / far background: not ground
            return None
        # rows v_split..h map linearly onto TOP..BOTTOM ground depth
        t = (v - self.v_split) / max(1, self.h - self.v_split)
        forward = FRAME_TOP_DEPTH_M + t * (FRAME_BOTTOM_DEPTH_M - FRAME_TOP_DEPTH_M)
        lateral = (u - self.w / 2.0) / PX_PER_M_LATERAL
        return forward, lateral


class LivePerceiver(threading.Thread):
    """Camera thread: frames -> detections -> ground points (callback)."""

    def __init__(self, camera_index: int, on_ground_point,
                 geometry: MastCameraGeometry | None = None,
                 use_yolo: bool = True):
        super().__init__(daemon=True)
        self.index = camera_index
        self.geometry = geometry                # rebuilt on the first frame
        self.on_ground_point = on_ground_point  # fn(fwd_m, lat_m, confidence)
        self._detector = None
        self._stop = threading.Event()
        self.last_error: str | None = None
        if use_yolo:
            try:
                from .detector import ResourceDetector
                self._detector = ResourceDetector()   # YOLO if trained, else CV
            except Exception:
                self._detector = None

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            import cv2
        except ImportError:
            self.last_error = "opencv-python is not installed - camera perception off"
            return

        from .detector import detect_baseline

        cap = cv2.VideoCapture(self.index)
        if not cap.isOpened():
            self.last_error = f"camera {self.index} could not be opened"
            return

        while not self._stop.is_set():
            t0 = time.time()
            ok, frame = cap.read()
            if not ok:
                self.last_error = "camera frame grab failed"
                time.sleep(1.0)
                continue
            frame = frame[::2, ::2]  # half resolution: Pi 5 CPU friendly
            h, w = frame.shape[:2]
            if self.geometry is None or self.geometry.w != w or self.geometry.h != h:
                self.geometry = MastCameraGeometry(w, h)
            geo = self.geometry

            # YOLO detector if a trained model exists, else the HSV baseline
            if self._detector is not None and self._detector.backend == "yolo":
                dets = self._detector.detect(frame)
            else:
                dets = detect_baseline(frame)

            for d in dets:
                x1, y1, x2, y2 = d.bbox_xyxy
                u, v = (x1 + x2) / 2.0, y2          # bottom-centre of the blob
                g = geo.to_ground(u, v)
                if g is None:
                    continue
                fwd, lat = g
                conf = float(np.clip(d.confidence, 0.0, 1.0))
                self.on_ground_point(fwd, lat, conf)

            self._stop.wait(max(0.0, GRAB_INTERVAL_S - (time.time() - t0)))
        cap.release()


def ground_to_world(pose_xyh: tuple[float, float, float],
                    forward_m: float, lateral_m: float) -> tuple[float, float]:
    """Camera-frame (forward, lateral) -> world (x, y) using the rover pose."""
    x, y, heading = pose_xyh
    dx = forward_m * math.cos(heading) - lateral_m * math.sin(heading)
    dy = forward_m * math.sin(heading) + lateral_m * math.cos(heading)
    return x + dx, y + dy
