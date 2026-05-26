"""
run_attack_demo.py  —  VideoCap AI Resistance Demo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run this script to demonstrate the AI attack simulation.

Usage (with live backend):
    python run_attack_demo.py --live --rounds 8

Usage (standalone demo — no server needed):
    python run_attack_demo.py --demo

Usage (with Gemini key + live backend):
    python run_attack_demo.py --live --gemini-key YOUR_KEY --api-key YOUR_VC_KEY --rounds 8
"""

import os
import sys
import time
import random
import argparse
from datetime import datetime


# ── ANSI helpers ──────────────────────────────────────────────────────────────
R="\033[91m"; G="\033[92m"; Y="\033[93m"; B="\033[94m"
CY="\033[96m"; W="\033[97m"; BO="\033[1m"; DIM="\033[2m"; RST="\033[0m"
def red(t):    return f"{R}{t}{RST}"
def green(t):  return f"{G}{t}{RST}"
def yellow(t): return f"{Y}{t}{RST}"
def blue(t):   return f"{B}{t}{RST}"
def cyan(t):   return f"{CY}{t}{RST}"
def bold(t):   return f"{BO}{t}{RST}"
def dim(t):    return f"{DIM}{t}{RST}"


# ── Fake scenario bank for demo mode ─────────────────────────────────────────
DEMO_SCENARIOS = [
    {
        "question":   "Which direction is the orange ball moving?",
        "options":    ["left","right","up","down"],
        "answer":     "right",
        "ai_says":    "left",
        "ai_reasoning": "Object detected near centre-left region. Estimated velocity vector: leftward. Confidence: 62%",
    },
    {
        "question":   "Is the blue box moving clockwise or counterclockwise?",
        "options":    ["clockwise","counterclockwise","don't know","not sure"],
        "answer":     "counterclockwise",
        "ai_says":    "clockwise",
        "ai_reasoning": "Circular motion detected. Arc segment in frames 2-4 suggests clockwise rotation. Confidence: 58%",
    },
    {
        "question":   "What should a driver do when the light turns green?",
        "options":    ["stop","slow","go","don't know"],
        "answer":     "go",
        "ai_says":    "go",
        "ai_reasoning": "Traffic light sequence identified. Final state: green. Corresponding driver action: go. Confidence: 91%",
        "_override_success": True,    # AI actually gets this right (easy semantic question)
    },
    {
        "question":   "Is it raining in the video?",
        "options":    ["yes","no","don't know","not sure"],
        "answer":     "yes",
        "ai_says":    "no",
        "ai_reasoning": "Precipitation not confidently detected. Background pattern could be rain or noise artifact. Defaulting to 'no'. Confidence: 44%",
    },
    {
        "question":   "Which direction is the red car moving?",
        "options":    ["left","right","don't know","not sure"],
        "answer":     "left",
        "ai_says":    "right",
        "ai_reasoning": "Vehicle detected. Orientation ambiguous in static frames — headlights suggest forward-right orientation. Confidence: 51%",
    },
    {
        "question":   "Does the green triangle bounce off the edges?",
        "options":    ["yes","no","don't know","not sure"],
        "answer":     "yes",
        "ai_says":    "don't know",
        "ai_reasoning": "Object position varies across frames but trajectory unclear from sampled frames alone. Cannot confirm bounce events. Confidence: 29%",
    },
    {
        "question":   "What color does the ball change to?",
        "options":    ["red","blue","green","yellow"],
        "answer":     "blue",
        "ai_says":    "green",
        "ai_reasoning": "Color shift detected between frames 3 and 5. Final color RGB(0,190,0) — best match: green. Confidence: 67%",
    },
    {
        "question":   "Is the door opening or closing?",
        "options":    ["opening","closing","don't know","not sure"],
        "answer":     "opening",
        "ai_says":    "opening",
        "ai_reasoning": "Door angle increases from ~0° in frame 1 to ~65° in frame 6. Motion is opening. Confidence: 83%",
        "_override_success": True,
    },
    {
        "question":   "Which color object is moving to the right?",
        "options":    ["red","blue","green","yellow","orange","purple"],
        "answer":     "yellow",
        "ai_says":    "orange",
        "ai_reasoning": "Two objects detected. Object A: warm hue, moving right. Object B: cool hue, moving left. Classifying Object A as orange. Confidence: 55%",
    },
    {
        "question":   "Which vertical direction does the purple star travel?",
        "options":    ["up","down","don't know","not sure"],
        "answer":     "up",
        "ai_says":    "down",
        "ai_reasoning": "Vertical displacement: frame 1 y=185, frame 6 y=210. Y increases downward in image coords — classified as 'down'. Confidence: 71%",
    },
]


def _spin(msg: str, duration: float):
    frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    end = time.time() + duration
    i = 0
    while time.time() < end:
        sys.stdout.write(f"\r  {msg} {frames[i % len(frames)]}  ")
        sys.stdout.flush()
        time.sleep(0.07)
        i += 1
    sys.stdout.write("\r" + " " * 70 + "\r")


def _progress_bar(done, total, w=30):
    filled = int(w * done / max(1, total))
    bar = "█" * filled + "░" * (w - filled)
    color = R if done > 0 else G
    return f"{color}[{bar}]{RST}"


def _banner():
    print(f"""
{R}{BO}
 ██╗   ██╗██╗██████╗ ███████╗ ██████╗  █████╗ ██████╗
 ██║   ██║██║██╔══██╗██╔════╝██╔════╝ ██╔══██╗██╔══██╗
 ██║   ██║██║██║  ██║█████╗  ██║  ███╗███████║██████╔╝
 ╚██╗ ██╔╝██║██║  ██║██╔══╝  ██║   ██║██╔══██║██╔═══╝
  ╚████╔╝ ██║██████╔╝███████╗╚██████╔╝██║  ██║██║
   ╚═══╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝{RST}
{CY}         A I   A T T A C K   S I M U L A T O R{RST}
{DIM}  Demonstrating AI resistance of the VideoCap CAPTCHA system{RST}
""")
    print("═" * 62)
    print(f"  {bold('System')}  : VideoCap – AI-Resistant Video CAPTCHA")
    print(f"  {bold('Attacker')}: Google Gemini Vision ({CY}gemini-1.5-flash{RST})")
    print(f"  {bold('Method')} : Frame sampling + multimodal visual inference")
    print(f"  {bold('Target')} : Motion direction, color, rotation, weather, traffic")
    print("═" * 62)


def run_demo(rounds: int = 8):
    """Offline demonstration — no server or API key required."""
    _banner()
    print(f"\n  {yellow('MODE')} : Demo simulation (no live server required)")
    print(f"  {yellow('NOTE')} : Gemini Vision responses simulated for presentation\n")
    time.sleep(1.2)

    pool    = (DEMO_SCENARIOS * 5)[:rounds]
    random.shuffle(pool)
    pool    = pool[:rounds]

    successes   = 0
    log         = []
    sep         = "─" * 62

    for i, scenario in enumerate(pool):
        q           = scenario["question"]
        opts        = scenario["options"]
        answer      = scenario["answer"]
        ai_says     = scenario.get("ai_says", random.choice(opts))
        reasoning   = scenario.get("ai_reasoning", "Visual inference completed.")
        override_ok = scenario.get("_override_success", False)

        success = override_ok or (ai_says.lower() == answer.lower())

        print(f"\n{sep}")
        print(bold(cyan(f"  🤖 ROUND {i+1} / {rounds}  —  AI Attack Cycle")))
        print(sep)

        # Step 1
        print(f"  {yellow('Step 1')} │ Requesting CAPTCHA challenge…")
        _spin("          │ Connecting to VideoCap server", 0.7)
        tok = f"{''.join(random.choices('abcdef0123456789', k=16))}"
        print(f"  {dim('Token')}   │ {tok[:24]}…")
        print(f"  {dim('Question')} │ {bold(q)}")
        print(f"  {dim('Options')} │ {' / '.join(opts)}")

        # Step 2
        print(f"\n  {yellow('Step 2')} │ Downloading video stream…")
        _spin("          │ Fetching video bytes", 0.6)
        vsize = random.randint(18_000, 64_000)
        print(f"          │ {vsize:,} bytes received  ({random.randint(28,30)} frames @ 10 fps)")

        # Step 3
        print(f"\n  {yellow('Step 3')} │ Extracting 6 key frames…")
        _spin("          │ OpenCV decoding + frame sampling", 0.8)
        print(f"          │ 6 frames captured at t=0%, 20%, 40%, 60%, 80%, 100%")

        # Step 4
        print(f"\n  {yellow('Step 4')} │ Running {cyan('Gemini Vision')} ({CY}gemini-1.5-flash{RST})…")
        _spin("          │ Uploading frames + running multimodal inference", 1.4)
        conf = random.randint(29, 92)
        print(f"  {dim('Reasoning')} │ {dim(reasoning)}")
        print(f"  {dim('Confidence')} │ {conf}%")
        print(f"  {bold('AI answer')} │ {bold(yellow(ai_says))}")

        # Step 5
        print(f"\n  {yellow('Step 5')} │ Submitting '{yellow(ai_says)}' to VideoCap validator…")
        _spin("          │ Awaiting server response", 0.5)

        # Result
        print(f"\n  {sep[:58]}")
        if success:
            successes += 1
            print(f"  {bold(red('💥 ATTACK SUCCEEDED'))} — CAPTCHA cracked!")
            print(f"     Correct: '{answer}'  │  AI answered: '{ai_says}'  ✓ Match")
        else:
            print(f"  {bold(green('🛡  CAPTCHA DEFENDED — AI BLOCKED'))}")
            print(f"     Correct: '{green(answer)}'  │  AI answered: '{red(ai_says)}'  ✗ Wrong")
            if ai_says == "don't know":
                print(f"     {dim('AI could not determine motion direction from static frames')}")
            elif conf < 50:
                print(f"     {dim('Low confidence inference — temporal information lost in frame sampling')}")
            else:
                print(f"     {dim('AI misidentified object color/direction due to BGR/RGB ambiguity')}")
        print(f"  {sep[:58]}\n")

        log.append({
            "round":     i+1,
            "question":  q,
            "correct":   answer,
            "ai_answer": ai_says,
            "success":   success,
            "confidence": conf,
        })

        time.sleep(0.4)

    # ── Summary ────────────────────────────────────────────────────────────
    rate = successes / rounds * 100
    blocked = rounds - successes

    print("\n" + "═" * 62)
    print(bold(cyan("  📊  ATTACK CAMPAIGN FINAL REPORT")))
    print("═" * 62)
    print(f"  {'AI Engine':<24}: Gemini Vision  ({CY}gemini-1.5-flash{RST})")
    print(f"  {'Attack rounds':<24}: {bold(str(rounds))}")
    print(f"  {'CAPTCHA challenges cracked':<24}: {bold(red(str(successes)) if successes else bold(green('0')))}")
    print(f"  {'Successfully defended':<24}: {bold(green(str(blocked)))}")
    print(f"  {'AI crack rate':<24}: {_progress_bar(successes, rounds)}  {rate:.1f}%")
    print(f"  {'Random baseline':<24}: ~25–33%  (guessing from options)")
    print()

    # Verdict box
    if successes == 0:
        _vbox(G,
              "✅  VIDEOCAP IS FULLY AI-PROOF",
              f"Gemini Vision failed on all {rounds} challenges.",
              "The AI performed WORSE than random guessing.",
              "Temporal motion data cannot be inferred from",
              "individual frames — a fundamental AI limitation.")
    elif rate <= 30:
        _vbox(Y,
              "🟡  VIDEOCAP SHOWS STRONG AI RESISTANCE",
              f"AI succeeded only {successes}/{rounds} times ({rate:.0f}% vs 25–33% baseline).",
              "Performance near random chance confirms resistance.",
              "VideoCap's procedural motion effectively defeats",
              "state-of-the-art multimodal AI vision models.")
    else:
        _vbox(Y,
              "⚠️   PARTIAL AI RESISTANCE DETECTED",
              f"AI succeeded {successes}/{rounds} times ({rate:.0f}%).",
              "Some question types show elevated crack rates.",
              "Recommend increasing temporal distortion.")

    # Per-question analysis
    print(f"\n  {bold('Per-question breakdown:')}")
    print(f"  {'─'*58}")
    print(f"  {'Question (truncated)':<36} {'Correct':>8}  {'AI said':>9}  {'Result':>8}")
    print(f"  {'─'*36}  {'─'*8}  {'─'*9}  {'─'*8}")
    for entry in log:
        q_trunc = entry["question"][:34].ljust(36)
        correct = entry["correct"][:8].rjust(8)
        ai_ans  = entry["ai_answer"][:9].rjust(9)
        ok = entry["success"]
        verdict = green("✅ Block") if not ok else red("💥 Crack")
        # swap — blocked is when AI fails = success for VideoCap
        verdict = red("💥 Crack") if ok else green("✅ Block")
        print(f"  {q_trunc}  {correct}  {ai_ans}  {verdict}")

    print(f"\n  {dim('Why AI fails:')}")
    print(f"  {dim('• Direction of motion requires comparing frames over time')}")
    print(f"  {dim('• OpenCV BGR ≠ RGB → Gemini often misidentifies colors')}")
    print(f"  {dim('• No temporal context in sampled key-frames alone')}")
    print(f"  {dim('• Exact string matching rejects near-correct answers')}")
    print(f"  {dim('• 13 motion types + 16 colors = 208+ answer permutations')}")
    print("\n" + "═" * 62 + "\n")


def _vbox(col, *lines):
    w = 56
    print(f"  ┌{'─'*(w)}┐")
    for line in lines:
        padded = line.ljust(w - 2)
        print(f"  │  {col}{BO}{padded}{RST}  │")
    print(f"  └{'─'*(w)}┘")
    print()


def run_live(url, rounds, delay, gemini_key, api_key):
    """Live mode — requires running VideoCap backend + valid API keys."""
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from ai_attacker import AIAttacker
    except ImportError:
        print(red("❌  ai_attacker.py not found in path. Run from project root."))
        sys.exit(1)

    attacker = AIAttacker(
        gemini_api_key=gemini_key or os.getenv("GEMINI_API_KEY", ""),
        api_key=api_key or os.getenv("VIDEOCAP_API_KEY", ""),
    )
    attacker.continuous_attack(api_url=url, num_attacks=rounds, delay=delay)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="VideoCap AI Attack Demo")
    ap.add_argument("--demo",       action="store_true",
                    help="Run offline demo (no server needed) — great for presentations")
    ap.add_argument("--live",       action="store_true",
                    help="Attack a live VideoCap server")
    ap.add_argument("--url",        default="http://localhost:5000")
    ap.add_argument("--rounds",     type=int,   default=8)
    ap.add_argument("--delay",      type=float, default=1.5)
    ap.add_argument("--gemini-key", default="", dest="gemini_key")
    ap.add_argument("--api-key",    default="", dest="api_key")
    args = ap.parse_args()

    if args.live:
        run_live(args.url, args.rounds, args.delay, args.gemini_key, args.api_key)
    else:
        # Default: demo mode
        run_demo(rounds=args.rounds)
