import os
import random
import hashlib
import uuid
import json
from datetime import datetime
import concurrent.futures

from ai_video_generator import AIVideoGenerator
import config


class VideoCaptchaGenerator:
    def __init__(self, base_videos_dir='base_videos', output_dir='generated_captchas', db=None):
        self.base_videos_dir = base_videos_dir
        self.output_dir = output_dir
        os.makedirs(self.base_videos_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        self.ai_generator = AIVideoGenerator(output_dir=output_dir, db=db)
        self._meta_cache = {}
        self._load_meta_cache()

    def _meta_path(self):
        return os.path.join(self.output_dir, '_meta.json')

    def _load_meta_cache(self):
        p = self._meta_path()
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    self._meta_cache = json.load(f)
            except:
                self._meta_cache = {}

    def get_cached_video(self):
        """Fallback: Pick random video from folder"""
        try:
            files = [f for f in os.listdir(self.output_dir) 
                    if f.endswith('.mp4') and not f.endswith('_raw.mp4') and not f.startswith('_')]
            if not files:
                return None

            random.shuffle(files)
            for fname in files:
                captcha_id = fname[:-4]
                meta = self._meta_cache.get(captcha_id)
                if meta and meta.get('question') and meta.get('answer'):
                    return {
                        'captcha_id': captcha_id,
                        'video_path': os.path.join(self.output_dir, fname),
                        'question': meta['question'],
                        'correct_answer': meta['answer'],
                        'from_cache': True,
                    }
            # Fallback
            fname = files[0]
            captcha_id = fname[:-4]
            return {
                'captcha_id': captcha_id,
                'video_path': os.path.join(self.output_dir, fname),
                'question': 'Which direction is the object moving?',
                'correct_answer': 'right',
                'from_cache': True,
            }
        except:
            return None

    def _generate_with_timeout(self, db):
        """Try to generate new video with 5 second timeout"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.ai_generator.generate_ai_video, 
                                   self.generate_unique_captcha_id())
            try:
                return future.result(timeout=5)
            except concurrent.futures.TimeoutError:
                print("⏱️ Generation took too long (>5s) - falling back to cached video")
                return None
            except Exception as e:
                print(f"❌ Generation error: {e} - falling back to cache")
                return None

    def generate_captcha(self, db):
        """Priority 1: Generate NEW video (max 5s). If fails → use cached video"""
        db.cleanup_expired_captchas()

        # Priority 1: Try to generate new video
        captcha_data = self._generate_with_timeout(db)

        if captcha_data:
            # New video generated successfully
            return {
                'captcha_id': captcha_data['video_id'],
                'video_path': captcha_data['video_path'],
                'question': captcha_data['question'],
                'correct_answer': captcha_data['answer'],
            }
        else:
            # Priority 2: Fallback to cached video from folder
            cached = self.get_cached_video()
            if cached:
                print("⚡ Using cached video from generated_captchas folder")
                return cached
            else:
                # Emergency fallback
                print("⚠️ No cached videos available.")
                return {
                    'captcha_id': 'fallback',
                    'video_path': '',
                    'question': 'Which direction is the object moving?',
                    'correct_answer': 'right',
                }

    def generate_unique_captcha_id(self):
        combined = f"ai_{datetime.now().timestamp()}_{uuid.uuid4()}_{os.urandom(8).hex()}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]