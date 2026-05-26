"""
Configuration settings for the Video CAPTCHA system
"""

# Server settings
HOST  = '0.0.0.0'
PORT  = 5000
DEBUG = True

# CAPTCHA settings
CAPTCHA_EXPIRY_MINUTES        = 5
MAX_CAPTCHA_GENERATION_ATTEMPTS = 100

# Video processing settings
VIDEO_WIDTH  = 320
VIDEO_HEIGHT = 240
VIDEO_FPS    = 8
MAX_FRAMES_PER_CAPTCHA = 50
MIN_FRAMES_PER_CAPTCHA = 10

# Frame sampling settings
MIN_SAMPLE_RATE = 0.6   # Keep at least 60 % of frames
MAX_SAMPLE_RATE = 0.9   # Keep at most  90 % of frames

# Speed variation settings
MIN_SPEED_FACTOR = 0.7   # Slowest playback
MAX_SPEED_FACTOR = 1.5   # Fastest playback

# Visual distortion settings
NOISE_PROBABILITY       = 0.7    # 70 % chance to add noise
ROTATION_PROBABILITY    = 0.5    # 50 % chance to rotate
COLOR_SHIFT_PROBABILITY = 0.6    # 60 % chance to shift colours
MAX_ROTATION_ANGLE      = 5      # Maximum rotation in degrees
MAX_BRIGHTNESS_FACTOR   = 1.2
MIN_BRIGHTNESS_FACTOR   = 0.8

# Database settings
MONGODB_CONNECTION_STRING = 'mongodb://localhost:27017/'
MONGODB_DATABASE_NAME     = 'video_captcha'

# Directory settings
BASE_VIDEOS_DIR = 'base_videos'
OUTPUT_DIR      = 'generated_captchas'

# ── Scenario settings ─────────────────────────────────────────────────────────
# Path to the JSON file that stores all scenario definitions.
# ScenarioManager reads from and writes to this file.
SCENARIOS_FILE = 'scenarios.json'

# Target number of scenarios in the pool.
# If the JSON has fewer than this number AND a Gemini API key is configured,
# ScenarioManager will automatically generate and append new scenarios on startup.
TARGET_SCENARIO_COUNT = 15

# ── Motion patterns (legacy – kept for backward compatibility) ────────────────
MOTION_PATTERNS = [
    {'name': 'left_to_right', 'question': 'Which direction does the object move?', 'answer': 'right'},
    {'name': 'right_to_left', 'question': 'Which direction does the object move?', 'answer': 'left'},
    {'name': 'up_to_down',    'question': 'Which direction does the object move?', 'answer': 'down'},
    {'name': 'down_to_up',    'question': 'Which direction does the object move?', 'answer': 'up'},
    {'name': 'clockwise',     'question': 'Does the object rotate clockwise or counterclockwise?', 'answer': 'clockwise'},
    {'name': 'counterclockwise', 'question': 'Does the object rotate clockwise or counterclockwise?', 'answer': 'counterclockwise'},
]