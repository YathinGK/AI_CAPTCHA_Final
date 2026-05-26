"""
ai_video_generator.py – COMPLETE HARDENED AI-Resistant Video CAPTCHA Generator
"""

import cv2
import numpy as np
import random
import math
import os
import hashlib
import subprocess
import json
from datetime import datetime

# ── AI Resistance Settings ───────────────────────────────────────────────────
NOISE_LEVEL = 30
ROTATION_MAX = 10
FRAMES_BASE = 40

COLORS = {
    "red": (0,0,210), "blue": (210,50,0), "green": (0,190,0),
    "yellow": (0,210,210), "orange": (0,130,255), "purple": (170,0,170),
    "pink": (180,100,255), "cyan": (210,210,0), "white": (240,240,240),
    "brown": (30,80,140), "lime": (0,230,100),
}
COLOR_NAMES = list(COLORS.keys())
OBJECT_TYPES = ["ball", "box", "triangle", "star", "diamond"]

class AIVideoGenerator:
    def __init__(self, output_dir="generated_captchas", scenarios_file="scenarios.json", db=None):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.W = 320
        self.H = 240
        self.FPS = 10

    def _meta_path(self):
        return os.path.join(self.output_dir, '_meta.json')

    def _save_meta(self, captcha_id, question, answer):
        meta = {}
        if os.path.exists(self._meta_path()):
            try:
                with open(self._meta_path(), 'r', encoding='utf-8') as f:
                    meta = json.load(f)
            except:
                pass
        meta[captcha_id] = {'question': question, 'answer': answer}
        try:
            with open(self._meta_path(), 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save meta: {e}")

    def _make_bg(self):
        bg = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        palette = [(220,220,220),(200,220,240),(200,240,200),(240,220,200)]
        bg[:] = random.choice(palette)
        return bg

    def _add_distortion(self, frame):
        frame = frame.copy()
        noise = np.random.normal(0, NOISE_LEVEL, frame.shape).astype(np.uint8)
        frame = cv2.add(frame, noise)
        if random.random() < 0.7:
            angle = random.uniform(-ROTATION_MAX, ROTATION_MAX)
            M = cv2.getRotationMatrix2D((self.W//2, self.H//2), angle, 1)
            frame = cv2.warpAffine(frame, M, (self.W, self.H), borderMode=cv2.BORDER_REPLICATE)
        return frame

    def _draw(self, frame, obj, x, y, size, color):
        x, y, size = int(x), int(y), max(5, int(size))
        cv2.circle(frame, (x,y), size, color, -1)

    def generate_ai_video(self, video_id: str) -> dict:
        obj = random.choice(OBJECT_TYPES)
        cn = random.choice(COLOR_NAMES)
        color = COLORS[cn]
        size = random.randint(12, 26)
        direction = random.choice(["left", "right"])

        bg = self._make_bg()
        frames = []
        for f in range(FRAMES_BASE):
            fr = bg.copy()
            t = f / FRAMES_BASE
            x = 30 + (self.W - 60) * t if direction == "right" else self.W - 30 - (self.W - 60) * t
            self._draw(fr, obj, int(x), self.H//2, size, color)
            fr = self._add_distortion(fr)
            frames.append(fr)

        question = f"Which direction is the {cn} {obj} moving?"
        answer = direction

        raw_path = os.path.join(self.output_dir, f"{video_id}_raw.mp4")
        final_path = os.path.join(self.output_dir, f"{video_id}.mp4")

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(raw_path, fourcc, self.FPS, (self.W, self.H))
        for f in frames:
            out.write(f)
        out.release()

        try:
            subprocess.run(["ffmpeg", "-y", "-i", raw_path, "-vcodec", "libx264", 
                           "-crf", "24", "-preset", "fast", "-pix_fmt", "yuv420p", final_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
            if os.path.exists(final_path):
                os.remove(raw_path)
                output_path = final_path
            else:
                output_path = raw_path
        except:
            output_path = raw_path

        self._save_meta(video_id, question, answer)

        print(f"✅ New Video Generated: {question} → {answer}")
        return {
            "video_id": video_id,
            "video_path": output_path,
            "question": question,
            "answer": answer
        }