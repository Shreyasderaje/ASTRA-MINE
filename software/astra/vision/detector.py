"""Resource-zone detection from camera frames.

Two detectors, both feeding the same interface:

1. Baseline (runs live on the Pi 5, no GPU, no training): HSV colour
   thresholding + contour analysis finds the rust-orange resource-marker
   pebbles and returns zone candidates as (bbox, confidence).

2. Optional YOLO: if `ultralytics` is installed and a model was trained with
   vision.dataset_gen + yolo CLI, it is used automatically for better
   accuracy. The code falls back gracefully to the baseline.

Both return a list of Detection(bbox_xyxy, confidence) in PIXEL space; the
mission controller converts them to grid-cell resource-probability updates.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# HSV range for the rust-orange resource markers (tune on the real testbed!)
HSV_LOW = (3, 70, 70)
HSV_HIGH = (25, 255, 255)


@dataclass
class Detection:
    bbox_xyxy: tuple[int, int, int, int]   # pixels
    confidence: float


def detect_baseline(frame_bgr: np.ndarray) -> list[Detection]:
    """Classic CV resource-marker detector (Pi-friendly, always available)."""
    blur = cv2.GaussianBlur(frame_bgr, (5, 5), 0)
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HSV_LOW, HSV_HIGH)
    # NOTE: no erosion/open here - marker pebbles are sparse dots, an open
    # would erase them. Closing only, to consolidate pebble clusters.
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: list[Detection] = []
    h, w = mask.shape
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 0.0015 * w * h:            # reject specks
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        fill = area / float(bw * bh)
        conf = float(np.clip(fill * 0.6 + min(1.0, area / (0.05 * w * h)) * 0.4, 0, 0.95))
        out.append(Detection((x, y, x + bw, y + bh), conf))
    return out


class ResourceDetector:
    """Auto-selecting detector: YOLO if available, else classic baseline."""

    def __init__(self, model_path: str | None = None):
        self._yolo = None
        try:
            from ultralytics import YOLO  # optional
            self._yolo = YOLO(model_path or "runs/detect/train/weights/best.pt")
        except Exception:
            self._yolo = None

    @property
    def backend(self) -> str:
        return "yolo" if self._yolo else "baseline-cv"

    def detect(self, frame_bgr: np.ndarray) -> list[Detection]:
        if self._yolo is not None:
            res = self._yolo.predict(frame_bgr, verbose=False)[0]
            out = []
            for b in res.boxes:
                x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
                out.append(Detection((int(x1), int(y1), int(x2), int(y2)),
                                     float(b.conf[0])))
            return out
        return detect_baseline(frame_bgr)


def frame_resource_score(frame_bgr: np.ndarray, detector: ResourceDetector | None = None,
                         frame_width_m: float = 0.9) -> tuple[float, list[Detection]]:
    """Convert a camera frame into a scalar resource-probability estimate for
    the ground under the rover (this feeds ResourceMapper.fuse on the real
    rover).

    score = max detection confidence over expected zone size, 0 if none.
    frame_width_m: how many metres of ground the frame covers (camera FOV).
    """
    det = detector or ResourceDetector()
    dets = det.detect(frame_bgr)
    h, w = frame_bgr.shape[:2]
    best = 0.0
    for d in dets:
        bw = (d.bbox_xyxy[2] - d.bbox_xyxy[0]) / w   # fraction of frame width
        # expected zone width at this height ~ 0.35 m
        size_match = 1.0 - abs(bw * frame_width_m - 0.35) / 0.7
        best = max(best, d.confidence * float(np.clip(size_match, 0.2, 1.0)))
    return float(np.clip(best, 0.0, 1.0)), dets


def annotate(frame_bgr: np.ndarray, dets: list[Detection]) -> np.ndarray:
    """Draw detections for the dashboard / demo video."""
    for d in dets:
        x1, y1, x2, y2 = d.bbox_xyxy
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (0, 200, 255), 2)
        cv2.putText(frame_bgr, f"resource {d.confidence:.2f}", (x1, max(12, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    return frame_bgr


if __name__ == "__main__":
    # self-test on one synthetic frame
    from .dataset_gen import render_frame
    rng = np.random.default_rng(3)
    img, bboxes = render_frame(320, rng, zone=True)
    frame = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    det = ResourceDetector()
    dets = det.detect(frame)
    score, _ = frame_resource_score(frame, det)
    print(f"backend: {det.backend}, detections: {len(dets)}, resource score: {score:.2f}")
    empty, _ = render_frame(320, rng, zone=False)
    score2, _ = frame_resource_score(cv2.cvtColor(empty, cv2.COLOR_RGB2BGR), det)
    print(f"empty frame score: {score2:.2f} (should be much lower)")
