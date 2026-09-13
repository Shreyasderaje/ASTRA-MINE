"""Synthetic training dataset generator for the resource-zone detector.

Renders top-down camera frames of the lunar analogue testbed the same way a
real Pi camera mounted ~1.2 m above the terrain would see it:

  * grey regolith base with per-pixel grain noise and lighting vignette
  * rocks as dark grey ellipses with a bright sun-side edge
  * resource zones as patches of rusty-orange marker pebbles (the physical
    testbed uses the same visual marker trick: resource proxies are marked
    with iron-oxide coloured gravel)
  * craters as soft dark gradients

Output (YOLO format, ready for training when you choose to):
    vision_dataset/images/train|val/*.jpg
    vision_dataset/labels/train|val/*.txt   (class x_center y_center w h)
    vision_dataset/dataset.yaml

Run (from software/):
    python -m astra.vision.dataset_gen --n 400
"""
from __future__ import annotations

import argparse
import os

import cv2
import numpy as np


def render_frame(size_px: int = 320, rng: np.random.Generator | None = None,
                 zone: bool = True, contrast: float = 0.55) -> tuple[np.ndarray, list]:
    """Render one synthetic frame. Returns (image, yolo_bboxes)."""
    rng = rng or np.random.default_rng()
    img = np.full((size_px, size_px, 3), 118, dtype=np.float32)

    # regolith grain: heavy fine noise, slight brown-grey tint
    grain = rng.normal(0, 9, (size_px, size_px, 1))
    tint = np.array([1.00, 0.97, 0.93])
    img = np.clip((img + grain) * tint, 0, 255)

    # craters: soft dark radial gradients
    for _ in range(rng.integers(0, 3)):
        cx, cy = rng.uniform(0, size_px, 2)
        rad = rng.uniform(size_px * 0.12, size_px * 0.3)
        yy, xx = np.mgrid[0:size_px, 0:size_px]
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        img -= (70 * np.exp(-d2 / (2 * (rad * 0.6) ** 2)))[..., None]

    bboxes = []
    # resource zone: rusty-orange pebble patch (class 0)
    if zone:
        cx, cy = rng.uniform(size_px * 0.3, size_px * 0.7, 2)
        rad = rng.uniform(size_px * 0.12, size_px * 0.22)
        yy, xx = np.mgrid[0:size_px, 0:size_px]
        mask = ((xx - cx) ** 2 + (yy - cy) ** 2) < rad ** 2
        pebbles = rng.random((size_px, size_px)) < 0.18
        patch = mask & pebbles
        rust = np.array([190.0, 95.0, 70.0])  # RGB rust orange (iron oxide)
        img[patch] = img[patch] * (1 - contrast) + rust * contrast
        # subtle dark halo around the zone (moisture proxy)
        halo = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (rad * 1.3) ** 2)))
        img -= (28 * halo)[..., None]
        bboxes.append([0,
                       float(cx / size_px), float(cy / size_px),
                       float(2.2 * rad / size_px), float(2.2 * rad / size_px)])

    # rocks: dark ellipses with sunlit edge
    for _ in range(rng.integers(2, 9)):
        cx, cy = rng.uniform(0, size_px, 2)
        w, h = rng.uniform(6, 18, 2)
        ang = rng.uniform(0, 180)
        rock = np.zeros((size_px, size_px), np.uint8)
        cv2.ellipse(rock, (int(cx), int(cy)), (int(w), int(h)), ang, 0, 360, 255, -1)
        img[rock > 0] *= 0.45
        edge = cv2.Canny(rock, 50, 150) > 0
        img[edge] = np.clip(img[edge] + 60, 0, 255)

    # vignette (camera + sun geometry)
    yy, xx = np.mgrid[0:size_px, 0:size_px]
    d = np.sqrt((xx - size_px / 2) ** 2 + (yy - size_px / 2) ** 2) / size_px
    img *= (1.0 - 0.35 * d[..., None] ** 2)

    return np.clip(img, 0, 255).astype(np.uint8), bboxes


def write_label(path: str, bboxes: list, n_classes: int = 1) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for b in bboxes:
            f.write(" ".join(str(x) for x in b) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic resource-zone dataset")
    ap.add_argument("--n", type=int, default=400, help="frames to generate")
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--out", default="vision_dataset")
    ap.add_argument("--size", type=int, default=320, help="frame size in px")
    args = ap.parse_args()

    rng = np.random.default_rng(7)
    n_val = max(1, int(args.n * args.val_frac))
    counts = {"train": 0, "val": 0}
    for i in range(args.n):
        split = "val" if i < n_val else "train"
        img_dir = os.path.join(args.out, "images", split)
        lbl_dir = os.path.join(args.out, "labels", split)
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(lbl_dir, exist_ok=True)

        zone = rng.random() < 0.7     # 70% positive frames
        img, bboxes = render_frame(args.size, rng, zone=zone)
        name = f"frame_{i:05d}.jpg"
        cv2.imwrite(os.path.join(img_dir, name),
                    cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        write_label(os.path.join(lbl_dir, name.replace(".jpg", ".txt")), bboxes)
        counts[split] += 1

    with open(os.path.join(args.out, "dataset.yaml"), "w", encoding="utf-8") as f:
        f.write(f"path: {os.path.abspath(args.out)}\n"
                "train: images/train\nval: images/val\n"
                "names:\n  0: resource_zone\n")

    print(f"dataset ready: {counts['train']} train / {counts['val']} val frames "
          f"-> {os.path.abspath(args.out)}")
    print("train with YOLO (optional):  pip install ultralytics && "
          "yolo detect train data=vision_dataset/dataset.yaml model=yolov8n.pt epochs=30")


if __name__ == "__main__":
    main()
