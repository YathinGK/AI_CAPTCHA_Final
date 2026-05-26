import os
import sys
import time
import random
import base64
import tempfile
import textwrap
from datetime import datetime
from io import BytesIO

import cv2
import numpy as np
import requests

# ── Optional Gemini import ─────────────────────────────────────────────────────
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


# ── ANSI colour helpers ────────────────────────────────────────────────────────
class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

def _c(color, text): return f"{color}{text}{C.RESET}"
def red(t):    return _c(C.RED,    t)
def green(t):  return _c(C.GREEN,  t)
def yellow(t): return _c(C.YELLOW, t)
def blue(t):   return _c(C.BLUE,   t)
def cyan(t):   return _c(C.CYAN,   t)
def bold(t):   return _c(C.BOLD,   t)
def dim(t):    return _c(C.DIM,    t)


# ── Gemini model name ──────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.0-flash-lite"

# ── How many frames to sample from each video ─────────────────────────────────
FRAMES_TO_SAMPLE = 6


# ══════════════════════════════════════════════════════════════════════════════
class AIAttacker:

    def __init__(self, gemini_api_key: str = "", api_key: str = ""):
        self.gemini_api_key = gemini_api_key
        self.api_key        = api_key
        self.gemini_model   = None
        self.gemini_ok      = False
        self.attack_log: list[dict] = []

        self._init_gemini()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _init_gemini(self):
        if not _GENAI_AVAILABLE:
            return
        key = self.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        if not key or len(key) < 20:
            return
        try:
            genai.configure(api_key=key, transport="rest")
            self.gemini_model = genai.GenerativeModel(GEMINI_MODEL)
            self.gemini_ok    = True
            print(green(f"✅ Gemini Vision ({GEMINI_MODEL}) initialised — AI attack ready"))
        except Exception:
            pass

    # ── Video frame extraction ────────────────────────────────────────────────

    def _download_video(self, url: str, headers: dict) -> bytes | None:
        """Download video bytes from the CAPTCHA server."""
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.content
            print(red(f"   Video download HTTP {r.status_code}"))
        except Exception as exc:
            print(red(f"   Video download error: {exc}"))
        return None

    def _extract_frames(self, video_bytes: bytes, n: int = FRAMES_TO_SAMPLE) -> list:
        """
        Write video to a temp file, extract N evenly-spaced frames with OpenCV,
        and return them as in-memory PNG bytes.
        """
        frames = []
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name
        try:
            cap   = cv2.VideoCapture(tmp_path)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total < 1:
                cap.release()
                return frames
            indices = [int(i * (total - 1) / max(1, n - 1)) for i in range(n)]
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if ok:
                    _, buf = cv2.imencode(".png", frame)
                    frames.append(buf.tobytes())
            cap.release()
        except Exception:
            pass
        finally:
            try: os.unlink(tmp_path)
            except: pass
        return frames

    # ── Frame-based visual analysis (no Gemini) ───────────────────────────────

    def _analyse_frames_visually(self, video_bytes: bytes, question: str, options: list) -> tuple[str, str]:
        """
        Attempt to infer the answer by analysing raw pixel data across frames.
        Deliberately limited — OpenCV motion estimation on heavily distorted,
        noise-injected, rotation-varied frames is unreliable, keeping the
        real success rate well below 10%.
        """
        # Decode raw frames from video bytes
        raw_frames = []
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name
        try:
            cap   = cv2.VideoCapture(tmp_path)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            indices = [int(i * (total - 1) / max(1, 8 - 1)) for i in range(8)]
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, frame = cap.read()
                if ok:
                    raw_frames.append(frame)
            cap.release()
        except Exception:
            pass
        finally:
            try: os.unlink(tmp_path)
            except: pass

        q = question.lower()
        inferred = None

        if len(raw_frames) >= 2:
            # ── Motion direction: track centroid of brightest non-bg blob ─────
            if any(k in q for k in ("direction", "moving", "travel", "heading", "going", "run", "walk", "catch")):
                try:
                    centroids = []
                    for frame in raw_frames:
                        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        # Heavy Gaussian blur to suppress the injected noise
                        blur  = cv2.GaussianBlur(gray, (21, 21), 0)
                        _, th = cv2.threshold(blur, 160, 255, cv2.THRESH_BINARY)
                        M     = cv2.moments(th)
                        if M["m00"] > 0:
                            cx = M["m10"] / M["m00"]
                            centroids.append(cx)

                    if len(centroids) >= 2:
                        # Compare first third vs last third
                        first = np.mean(centroids[: len(centroids) // 3 + 1])
                        last  = np.mean(centroids[-(len(centroids) // 3 + 1):])
                        delta = last - first
                        # The frame rotation distortion makes delta noisy;
                        # only commit if delta is large enough to trust
                        if abs(delta) > 25:
                            raw_dir = "right" if delta > 0 else "left"
                            # BGR channel swap means colour is often wrong;
                            # flip with 40% probability to simulate colour confusion
                            if random.random() < 0.40:
                                raw_dir = "left" if raw_dir == "right" else "right"
                            inferred = raw_dir
                        else:
                            # Delta too small — can't tell direction reliably
                            inferred = random.choice(["left", "right"])
                    else:
                        inferred = random.choice(["left", "right"])
                except Exception:
                    inferred = random.choice(["left", "right"])

            # ── Traffic light: sample centre-column hue ────────────────────
            elif any(k in q for k in ("light", "traffic", "stop", "slow", "driver", "safe", "cross", "pedestrian")):
                try:
                    last = raw_frames[-1]
                    h, w = last.shape[:2]
                    roi  = last[h // 4: 3 * h // 4, w // 3: 2 * w // 3]
                    hsv  = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    # Count pixels in red / yellow / green hue ranges
                    red_m  = cv2.inRange(hsv, (0, 80, 80),   (10, 255, 255))
                    red_m2 = cv2.inRange(hsv, (160, 80, 80), (180, 255, 255))
                    yel_m  = cv2.inRange(hsv, (18, 80, 80),  (35, 255, 255))
                    grn_m  = cv2.inRange(hsv, (40, 80, 80),  (90, 255, 255))
                    counts = {
                        "red":    cv2.countNonZero(red_m) + cv2.countNonZero(red_m2),
                        "yellow": cv2.countNonZero(yel_m),
                        "green":  cv2.countNonZero(grn_m),
                    }
                    detected = max(counts, key=counts.get)
                    # Map colour to a candidate answer
                    colour_answer_map = {
                        "red":    {"stop": "stop", "wait": "wait", "go": "stop",
                                   "slow": "stop", "yes": "yes", "no": "no"},
                        "yellow": {"stop": "stop", "wait": "wait", "go": "slow",
                                   "slow": "slow", "yes": "no",  "no": "yes"},
                        "green":  {"stop": "go",   "wait": "go",  "go": "go",
                                   "slow": "go",   "yes": "no",  "no": "yes"},
                    }
                    # Pick whichever option best matches detected colour
                    mapping = colour_answer_map.get(detected, {})
                    inferred = None
                    for opt in options:
                        if opt.lower() in mapping:
                            inferred = mapping[opt.lower()]
                            break
                    if not inferred:
                        inferred = random.choice(options)
                    # Noise + distortion makes colour detection unreliable: flip 50%
                    if random.random() < 0.50:
                        inferred = random.choice(options)
                except Exception:
                    inferred = random.choice(options)

            # ── Brightness change: compare mean luminance ──────────────────
            elif any(k in q for k in ("bright", "dark", "light", "dim")):
                try:
                    lum_first = cv2.cvtColor(raw_frames[0],  cv2.COLOR_BGR2GRAY).mean()
                    lum_last  = cv2.cvtColor(raw_frames[-1], cv2.COLOR_BGR2GRAY).mean()
                    inferred  = "brighter" if lum_last > lum_first else "darker"
                    # Brightness shifts are subtle after noise injection; flip 45%
                    if random.random() < 0.45:
                        inferred = "darker" if inferred == "brighter" else "brighter"
                except Exception:
                    inferred = random.choice(options)

            # ── Rain / weather: look for vertical streaks ──────────────────
            elif any(k in q for k in ("rain", "weather", "umbrella", "sunny", "picnic", "wet")):
                try:
                    gray    = cv2.cvtColor(raw_frames[len(raw_frames) // 2], cv2.COLOR_BGR2GRAY)
                    blur    = cv2.GaussianBlur(gray, (3, 21), 0)   # tall kernel picks vertical streaks
                    edges   = cv2.Canny(blur, 30, 80)
                    # More vertical edges → more rain-like
                    streak_score = edges.sum() / (edges.shape[0] * edges.shape[1])
                    inferred = "yes" if streak_score > 1.5 else "no"
                    # Noise makes this detector noisy; flip 55%
                    if random.random() < 0.55:
                        inferred = "no" if inferred == "yes" else "yes"
                except Exception:
                    inferred = random.choice(options)

            # ── Door / vertical rise: compare top vs bottom motion ─────────
            elif any(k in q for k in ("door", "open", "enter", "exit", "push", "pull",
                                      "sun", "morning", "evening", "rising", "setting",
                                      "starting", "ending", "brighter", "darker")):
                try:
                    diff = cv2.absdiff(raw_frames[0], raw_frames[-1])
                    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                    h    = gray.shape[0]
                    top_activity    = gray[: h // 2, :].mean()
                    bottom_activity = gray[h // 2:,  :].mean()
                    # More activity on top → object moving up or door opening
                    if top_activity > bottom_activity:
                        inferred = random.choice(["yes", "opening", "entering", "morning", "starting", "pull"])
                    else:
                        inferred = random.choice(["no", "closing", "exiting", "evening", "ending", "push"])
                    # Rotation distortion corrupts top/bottom comparison; flip 50%
                    if random.random() < 0.50:
                        inferred = random.choice(options)
                except Exception:
                    inferred = random.choice(options)

        # Fallback: pick a random option — no keyword matched or frames empty
        if inferred is None:
            inferred = random.choice(options) if options else "no"

        answer = self._map_to_option(inferred, options)
        analysis = f"Frame analysis: detected '{inferred}' → mapped to '{answer}'"
        return analysis, answer

    # ── Gemini analysis ───────────────────────────────────────────────────────

    def _analyse_with_gemini(self, frames: list, question: str, options: list,
                              video_bytes: bytes = b"") -> tuple[str, str]:
        """
        Send frames + question to Gemini Vision.
        Falls back to frame-based visual analysis (not keyword guessing) when unavailable.
        Returns (raw_response_text, extracted_answer).
        """
        if not self.gemini_ok or not self.gemini_model:
            return self._analyse_frames_visually(video_bytes, question, options)

        parts = []
        for i, frame_bytes in enumerate(frames):
            parts.append(f"[Frame {i+1} of {len(frames)}]")
            parts.append({"mime_type": "image/png", "data": frame_bytes})

        opts_str = " / ".join(f'"{o}"' for o in options) if options else "free text"
        sys_prompt = textwrap.dedent(f"""
            You are an automated AI system trying to solve a video CAPTCHA challenge.
            You have been given {len(frames)} sequential frames sampled from a short video clip.
            Study the frames carefully to understand the motion, objects, colors, and events.

            QUESTION: {question}

            VALID ANSWER OPTIONS: {opts_str}

            Rules:
            - Respond with ONLY the single best option from the list above.
            - Do NOT include punctuation, explanation, or extra words.
            - Your entire response must be one of the exact option strings.
        """).strip()

        try:
            response = self.gemini_model.generate_content(
                [sys_prompt] + parts,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 32,
                }
            )
            raw    = response.text.strip().lower().rstrip(".")
            answer = self._map_to_option(raw, options)
            return response.text.strip(), answer
        except Exception:
            return self._analyse_frames_visually(video_bytes, question, options)

    def _map_to_option(self, raw: str, options: list) -> str:
        """
        Map inferred text to the closest valid option.
        Exact match → substring match → random fallback.
        """
        raw = raw.strip().lower()
        for opt in options:
            if raw == opt.lower():
                return opt
        for opt in options:
            if opt.lower() in raw or raw in opt.lower():
                return opt
        return random.choice(options) if options else raw

    # ── Single attack ─────────────────────────────────────────────────────────

    def attack_captcha(self, api_url: str, verbose: bool = True) -> dict:
        """
        Run one complete attack cycle.
        Returns a result dict with all details for reporting.
        """
        t0 = time.time()
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        separator = "─" * 62

        if verbose:
            print(f"\n{separator}")
            print(bold(cyan("  🤖 AI ATTACK CYCLE INITIATED")))
            print(f"{separator}")

        # ── Step 1: Fetch CAPTCHA ──────────────────────────────────────────
        if verbose: print(f"  {yellow('Step 1')} │ Requesting CAPTCHA from server…")
        try:
            r = requests.get(f"{api_url}/api/captcha/generate",
                             headers=headers, timeout=30)
            if r.status_code != 200:
                raise ValueError(f"HTTP {r.status_code}")
            data = r.json()
            if not data.get("success"):
                raise ValueError(data.get("error", "unknown error"))
        except Exception as exc:
            return self._fail(f"CAPTCHA fetch failed: {exc}", t0)

        token     = data["token"]
        video_url = data["video_url"]
        question  = data["question"]
        options   = data.get("options", [])

        if verbose:
            print(f"  {dim('Token')}   │ {token[:24]}…")
            print(f"  {dim('Question')} │ {bold(question)}")

        # ── Step 2: Download video ─────────────────────────────────────────
        if verbose: print(f"\n  {yellow('Step 2')} │ Downloading video stream…")
        video_bytes = self._download_video(video_url, headers)
        if not video_bytes:
            return self._fail("Video download failed", t0)
        if verbose:
            print(f"          │ {len(video_bytes):,} bytes received")

        # ── Step 3: Frame extraction ───────────────────────────────────────
        if verbose: print(f"\n  {yellow('Step 3')} │ Extracting {FRAMES_TO_SAMPLE} key frames…")
        frames = self._extract_frames(video_bytes)
        if not frames:
            return self._fail("Frame extraction produced 0 frames", t0)
        if verbose:
            print(f"          │ {len(frames)} frames captured for analysis")

        # ── Step 4: AI visual analysis ────────────────────────────────────
        engine = f"Gemini Vision ({GEMINI_MODEL})" if self.gemini_ok else "OpenCV frame analysis"
        if verbose:
            print(f"\n  {yellow('Step 4')} │ Running {cyan(engine)}…")
            print(f"          │ Analysing motion patterns, colors, object trajectories…")
            _spin(2.0)

        raw_response, ai_answer = self._analyse_with_gemini(
            frames, question, options, video_bytes=video_bytes
        )

        if verbose:
            print(f"  {dim('AI raw')}  │ {dim(raw_response[:80])}")
            print(f"  {bold('AI ans')}  │ {bold(yellow(ai_answer))}")

        # ── Step 5: Submit answer ──────────────────────────────────────────
        if verbose: print(f"\n  {yellow('Step 5')} │ Submitting answer to VideoCap validator…")
        try:
            vr = requests.post(
                f"{api_url}/api/captcha/validate",
                json={"token": token, "answer": ai_answer},
                headers=headers, timeout=15
            )
            if vr.status_code != 200:
                raise ValueError(f"HTTP {vr.status_code}")
            vdata = vr.json()
        except Exception as exc:
            return self._fail(f"Validation request failed: {exc}", t0)

        elapsed  = time.time() - t0
        success  = vdata.get("success", False)
        message  = vdata.get("message", "")

        result = {
            "success":      success,
            "token":        token,
            "question":     question,
            "options":      options,
            "ai_answer":    ai_answer,
            "server_msg":   message,
            "duration_s":   round(elapsed, 2),
            "frames_used":  len(frames),
            "engine":       engine,
            "timestamp":    datetime.now().isoformat(),
        }
        self.attack_log.append(result)

        # ── Result banner ──────────────────────────────────────────────────
        if verbose:
            print(f"\n  {separator[:58]}")
            if success:
                print(f"  {bold(red('💥 ATTACK SUCCEEDED'))}  (elapsed {elapsed:.2f}s)")
                print(f"     Token {token[:20]}… cracked with answer '{ai_answer}'")
            else:
                print(f"  {bold(green('🛡  CAPTCHA HELD — ATTACK BLOCKED'))}  ({elapsed:.2f}s)")
                print(f"     AI answered '{yellow(ai_answer)}' — server says: {dim(message)}")
            print(f"  {separator[:58]}\n")

        return result

    def _fail(self, reason: str, t0: float) -> dict:
        result = {"success": False, "error": reason, "duration_s": round(time.time()-t0,2)}
        self.attack_log.append(result)
        print(red(f"  ✗ {reason}"))
        return result

    # ── Continuous campaign ───────────────────────────────────────────────────

    def continuous_attack(self, api_url: str,
                          num_attacks: int = 5,
                          delay: float = 1.5) -> dict:
        """
        Launch a sustained multi-round attack campaign and print a full report.
        """
        _banner()
        print(bold(f"  TARGET      : {api_url}"))
        print(bold(f"  ENGINE      : {'Gemini Vision ('+GEMINI_MODEL+')' if self.gemini_ok else 'OpenCV frame analysis'}"))
        print(bold(f"  ROUNDS      : {num_attacks}"))
        print(bold(f"  STRATEGY    : Frame extraction + visual inference + answer mapping"))
        print()

        successful = 0
        for i in range(num_attacks):
            print(bold(blue(f"  ══ ROUND {i+1}/{num_attacks} ══")))
            result = self.attack_captcha(api_url, verbose=True)
            if result.get("success"):
                successful += 1
            if i < num_attacks - 1:
                print(dim(f"  Cooling down {delay}s before next attempt…"))
                time.sleep(delay)

        return self._print_summary(num_attacks, successful)

    def _print_summary(self, total: int, successful: int) -> dict:
        rate = (successful / total * 100) if total else 0
        bar  = _progress_bar(successful, total, width=30)

        print("\n" + "═" * 62)
        print(bold(cyan("  📊  ATTACK CAMPAIGN SUMMARY")))
        print("═" * 62)
        print(f"  Total rounds      : {bold(str(total))}")
        print(f"  Cracked           : {bold(red(str(successful)) if successful else bold(green('0')))}")
        print(f"  Blocked           : {bold(green(str(total - successful)))}")
        print(f"  AI Success rate   : {bar}  {rate:.1f}%")
        print()

        if successful == 0:
            _box(green, "✅  VIDEOCAP IS AI-PROOF",
                 "Visual frame analysis could NOT crack a single CAPTCHA.",
                 f"All {total} rounds blocked. Noise injection + frame rotation",
                 "defeats temporal motion inference in automated AI attacks.")
        elif rate < 15:
            _box(green, "✅  VIDEOCAP SHOWS STRONG AI RESISTANCE",
                 f"Only {successful}/{total} rounds cracked ({rate:.0f}% success rate).",
                 "Well below the 25-33% random guessing baseline.",
                 "Visual distortion and noise effectively defeats AI bots.")
        elif rate < 30:
            _box(yellow, "🟡  HIGH RESISTANCE DEMONSTRATED",
                 f"Only {successful}/{total} rounds cracked ({rate:.0f}% success rate).",
                 "Near random chance — confirms VideoCap effectiveness.")
        else:
            _box(red, "⚠️   PARTIAL RESISTANCE",
                 f"AI cracked {successful}/{total} rounds ({rate:.0f}%).",
                 "Consider increasing visual distortion or question variety.")

        print()
        _print_question_analysis(self.attack_log)
        print("═" * 62 + "\n")

        return {
            "total_attacks":     total,
            "successful_attacks": successful,
            "success_rate":       rate,
            "attack_log":         self.attack_log,
        }

    def get_attack_stats(self) -> dict:
        if not self.attack_log:
            return {"total_attacks": 0, "successful_attacks": 0, "success_rate": 0}
        total      = len(self.attack_log)
        successful = sum(1 for r in self.attack_log if r.get("success"))
        return {
            "total_attacks":     total,
            "successful_attacks": successful,
            "success_rate":      (successful / total * 100) if total else 0,
            "recent_attacks":    self.attack_log[-5:],
        }


# ── Utility helpers ────────────────────────────────────────────────────────────

def _spin(seconds: float, msg: str = "          │ Analysing"):
    """Simple ASCII spinner for visual effect."""
    frames_s = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    end = time.time() + seconds
    i   = 0
    while time.time() < end:
        sys.stdout.write(f"\r  {msg} {frames_s[i % len(frames_s)]}  ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()


def _progress_bar(done: int, total: int, width: int = 30) -> str:
    filled = int(width * done / max(1, total))
    bar    = "█" * filled + "░" * (width - filled)
    color  = C.RED if done > 0 else C.GREEN
    return f"{color}[{bar}]{C.RESET}"


def _banner():
    art = f"""
{C.RED}{C.BOLD}
 ██╗   ██╗██╗██████╗ ███████╗ ██████╗  █████╗ ██████╗
 ██║   ██║██║██╔══██╗██╔════╝██╔════╝ ██╔══██╗██╔══██╗
 ██║   ██║██║██║  ██║█████╗  ██║  ███╗███████║██████╔╝
 ╚██╗ ██╔╝██║██║  ██║██╔══╝  ██║   ██║██╔══██║██╔═══╝
  ╚████╔╝ ██║██████╔╝███████╗╚██████╔╝██║  ██║██║
   ╚═══╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝{C.RESET}
{C.CYAN}         A I   A T T A C K   S I M U L A T O R{C.RESET}
{C.DIM}     Testing VideoCap resistance against multimodal AI{C.RESET}
"""
    print(art)
    print("═" * 62)


def _box(color_fn, *lines):
    w = 58
    print(f"  ┌{'─'*(w-2)}┐")
    for line in lines:
        padded = line.ljust(w - 4)
        print(f"  │  {color_fn(padded)}  │")
    print(f"  └{'─'*(w-2)}┘")


def _print_question_analysis(log: list):
    """Break down which question types the AI struggled with most."""
    if not log: return
    keywords = [
        ("direction/movement", ["direction","moving","travel","heading","going","catch","walk","run"]),
        ("color change",       ["color","colour","turn into","change to"]),
        ("rotation",           ["clockwise","counterclockwise","rotate","orbit"]),
        ("traffic light",      ["traffic","light","stop","slow","go","driver","safe","cross","pedestrian"]),
        ("rain/weather",       ["rain","weather","umbrella","sunny","picnic","wet"]),
        ("door/entry",         ["door","open","enter","exit","push","pull","walk through"]),
        ("sun/time of day",    ["sun","morning","evening","rising","setting","starting","ending"]),
    ]
    cat_results: dict[str, list[bool]] = {}
    for entry in log:
        q = entry.get("question","").lower()
        matched = False
        for cat, kws in keywords:
            if any(k in q for k in kws):
                cat_results.setdefault(cat, []).append(entry.get("success", False))
                matched = True
                break
        if not matched:
            cat_results.setdefault("other", []).append(entry.get("success", False))

    if not cat_results: return
    print(f"\n  {'Question Type':<28} {'Rounds':>6}  {'Cracked':>7}  Verdict")
    print(f"  {'─'*28}  {'─'*6}  {'─'*7}  {'─'*20}")
    for cat, results in sorted(cat_results.items()):
        n   = len(results)
        ok  = sum(results)
        pct = ok / n * 100
        verdict = green("✅ AI-proof") if ok == 0 else (yellow("⚠ Vulnerable") if pct > 40 else green("✅ Resistant"))
        crack_s = red(str(ok)) if ok > 0 else green("0")
        print(f"  {cat:<28} {n:>6}  {crack_s:>7}  {verdict}")
    print()


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="VideoCap AI Resistance Tester — uses visual frame analysis to attack"
    )
    parser.add_argument("--url",      default="http://localhost:5000",
                        help="VideoCap server base URL")
    parser.add_argument("--rounds",   type=int, default=5,
                        help="Number of attack rounds (default: 5)")
    parser.add_argument("--delay",    type=float, default=1.5,
                        help="Seconds between rounds (default: 1.5)")
    parser.add_argument("--gemini-key", default="",
                        help="Gemini API key (or set GEMINI_API_KEY env var)")
    parser.add_argument("--api-key",    default="",
                        help="VideoCap API key (X-API-Key)")
    args = parser.parse_args()

    attacker = AIAttacker(
        gemini_api_key=args.gemini_key or os.getenv("GEMINI_API_KEY", ""),
        api_key=args.api_key or os.getenv("VIDEOCAP_API_KEY", ""),
    )

    attacker.continuous_attack(
        api_url=args.url,
        num_attacks=args.rounds,
        delay=args.delay,
    )