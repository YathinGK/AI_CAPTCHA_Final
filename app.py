import os
import logging
import concurrent.futures
from functools import wraps

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from database import CaptchaDatabase
from captcha_generator import VideoCaptchaGenerator
from api_key_manager import APIKeyManager
import config

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})   # allow all for widget calls

# ── Components ────────────────────────────────────────────────────────────────
db         = CaptchaDatabase(config.MONGODB_CONNECTION_STRING, config.MONGODB_DATABASE_NAME)
captcha_gen = VideoCaptchaGenerator(config.BASE_VIDEOS_DIR, config.OUTPUT_DIR, db=db.db)
key_mgr    = APIKeyManager(db.db)     # reuse the same pymongo db object

# ── Generation timeout (seconds) ──────────────────────────────────────────────
GENERATION_TIMEOUT_SEC = 3


# ── Helpers ───────────────────────────────────────────────────────────────────

def generate_smart_options(correct_answer: str) -> list:
    import random
    groups = {
        'yes': ['yes','no',"don't know",'not sure'],
        'no':  ['no','yes',"don't know",'not sure'],
        'left': ['left','right',"don't know",'not sure'],
        'right':['right','left',"don't know",'not sure'],
        'up':   ['up','down',"don't know",'not sure'],
        'down': ['down','up',"don't know",'not sure'],
        'clockwise':       ['clockwise','counterclockwise',"don't know",'not sure'],
        'counterclockwise':['counterclockwise','clockwise',"don't know",'not sure'],
        'stop': ['stop','go',"don't know",'not sure'],
        'go':   ['go','stop',"don't know",'not sure'],
        'morning':  ['morning','evening',"don't know",'not sure'],
        'evening':  ['evening','morning',"don't know",'not sure'],
        'rainy':    ['rainy','sunny',"don't know",'not sure'],
        'sunny':    ['sunny','rainy',"don't know",'not sure'],
        'brighter': ['brighter','darker',"don't know",'not sure'],
        'darker':   ['darker','brighter',"don't know",'not sure'],
        'starting': ['starting','ending',"don't know",'not sure'],
        'ending':   ['ending','starting',"don't know",'not sure'],
        'more':     ['more','less',"don't know",'not sure'],
        'less':     ['less','more',"don't know",'not sure'],
        'entering': ['entering','exiting',"don't know",'not sure'],
        'wait': ['wait','go','slow',"don't know"],
        'slow': ['slow','wait','go',"don't know"],
        'away': ['away','closer',"don't know",'not sure'],
        'pull': ['pull','push',"don't know",'not sure'],
        'push': ['push','pull',"don't know",'not sure'],
    }
    options = groups.get(correct_answer.lower(),
                         [correct_answer, 'no' if correct_answer!='no' else 'yes',
                          "don't know", 'not sure'])
    if correct_answer not in options:
        options[0] = correct_answer
    random.shuffle(options)
    return options


def _generate_with_timeout(db_obj) -> dict:
    """
    Attempt to generate a fresh CAPTCHA video.
    Raises concurrent.futures.TimeoutError if it takes longer than
    GENERATION_TIMEOUT_SEC seconds, so callers can fall back to cache.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(captcha_gen.generate_captcha, db_obj)
        return future.result(timeout=GENERATION_TIMEOUT_SEC)


def _serve_cached_fallback() -> dict | None:
    """
    Pick a random cached video from generated_captchas/.
    Returns a captcha_data dict compatible with the generate endpoints,
    or None if no cached videos exist.
    """
    cached = captcha_gen.get_cached_video()
    if cached:
        logger.info(f"⚡ Serving cached video: {cached['captcha_id']}")
    return cached


# ── API-key middleware decorator ──────────────────────────────────────────────

def require_api_key(f):
    """Decorator: validates X-API-Key header (or ?api_key= param).
    In DEBUG mode, requests from localhost or null origin are allowed without
    a valid key so the demo HTML works when opened as a local file.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import g
        raw_key = (request.headers.get("X-API-Key") or
                   request.args.get("api_key") or "")
        origin  = request.headers.get("Origin", "")

        # Allow localhost / file:// (null origin) in DEBUG mode
        is_local = origin in ("", "null") or origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1")
        if config.DEBUG and is_local:
            g.api_key_doc = {"plan": "free", "key_id": "debug"}
            return f(*args, **kwargs)

        ok, reason, key_doc = key_mgr.validate_key(raw_key, origin)
        if not ok:
            logger.warning(f"API key rejected: {reason}  origin={origin}")
            return jsonify({"success": False, "error": reason}), 401

        g.api_key_doc = key_doc
        return f(*args, **kwargs)
    return decorated


# ═════════════════════════════════════════════════════════════════════════════
# ── API KEY MANAGEMENT ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/keys/create", methods=["POST"])
def create_api_key():
    data = request.get_json() or {}
    email = data.get("owner_email", "").strip()
    name  = data.get("owner_name",  "").strip()
    plan  = data.get("plan", "free").strip()

    if not email or not name:
        return jsonify({"success": False, "error": "owner_email and owner_name required"}), 400

    if plan not in ("free", "pro", "enterprise"):
        plan = "free"

    key_info = key_mgr.create_key(email, name, plan)
    logger.info(f"New API key created for {email}  plan={plan}")

    return jsonify({
        "success": True,
        "message": "API key created. Save this API key – it will NOT be shown again.",
        "api_key": key_info.get("raw_key"),
        "key": {
            "key_id": key_info.get("key_id"),
            "owner_email": key_info.get("owner_email"),
            "plan": key_info.get("plan"),
            "monthly_limit": key_info.get("monthly_limit"),
            "created_at": key_info.get("created_at")
        }
    }), 201


@app.route("/api/keys", methods=["GET"])
def list_api_keys():
    email = request.args.get("email", "").strip()
    if not email:
        return jsonify({"success": False, "error": "email query param required"}), 400
    keys = key_mgr.list_keys(email)
    return jsonify({"success": True, "keys": keys})


@app.route("/api/keys/<key_id>", methods=["GET"])
def get_api_key(key_id):
    info = key_mgr.get_key_info(key_id)
    if not info:
        return jsonify({"success": False, "error": "Key not found"}), 404
    return jsonify({"success": True, "key": info})


@app.route("/api/keys/<key_id>/revoke", methods=["POST"])
def revoke_api_key(key_id):
    ok = key_mgr.revoke_key(key_id)
    if not ok:
        return jsonify({"success": False, "error": "Key not found or already revoked"}), 404
    logger.info(f"API key revoked: {key_id}")
    return jsonify({"success": True, "message": f"Key {key_id} revoked"})


@app.route("/api/keys/<key_id>/domains", methods=["POST"])
def set_domains(key_id):
    data    = request.get_json() or {}
    domains = data.get("domains", [])
    ok = key_mgr.set_allowed_domains(key_id, domains)
    if not ok:
        return jsonify({"success": False, "error": "Key not found"}), 404
    return jsonify({"success": True, "allowed_domains": domains})


# ═════════════════════════════════════════════════════════════════════════════
# ── THIRD-PARTY INTEGRATION ENDPOINTS  (require API key)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/captcha/generate", methods=["GET"])
@require_api_key
def ext_generate_captcha():
    """
    Third-party CAPTCHA generation with 3-second timeout fallback.
    If fresh generation takes > 3 s, a cached video is returned instead.
    """
    try:
        db.cleanup_expired_captchas()

        captcha_data = None
        from_cache   = False

        # ── Try live generation (3 s budget) ──────────────────────────────
        try:
            captcha_data = _generate_with_timeout(db)
        except (concurrent.futures.TimeoutError, Exception) as exc:
            logger.warning(f"Live generation failed/timed-out ({exc}), falling back to cache")
            captcha_data = _serve_cached_fallback()
            from_cache   = True

        if not captcha_data:
            return jsonify({"success": False, "error": "No CAPTCHA available (generation failed and cache is empty)"}), 500

        correct_answer = captcha_data["correct_answer"]
        options        = generate_smart_options(correct_answer)

        db.store_captcha(
            captcha_data["captcha_id"],
            captcha_data["correct_answer"],
            captcha_data["question"],
            expiry_minutes=config.CAPTCHA_EXPIRY_MINUTES,
        )

        base_url = request.host_url.rstrip("/")

        return jsonify({
            "success":    True,
            "token":      captcha_data["captcha_id"],
            "video_url":  f"{base_url}/api/captcha/video/{captcha_data['captcha_id']}",
            "question":   captcha_data["question"],
            "options":    options,
            "from_cache": from_cache,
            "expires_in": config.CAPTCHA_EXPIRY_MINUTES * 60,
        })

    except Exception as exc:
        logger.error(f"ext_generate_captcha error: {exc}")
        return jsonify({"success": False, "error": "Failed to generate CAPTCHA"}), 500


@app.route("/api/captcha/video/<captcha_id>")
@require_api_key
def ext_serve_video(captcha_id):
    """Serve video for external integrations (API-key protected)."""
    video_path = os.path.join(captcha_gen.output_dir, f"{captcha_id}.mp4")
    if not os.path.exists(video_path):
        # ffmpeg may not be available — fall back to raw mp4
        raw_path = os.path.join(captcha_gen.output_dir, f"{captcha_id}_raw.mp4")
        if os.path.exists(raw_path):
            video_path = raw_path
        else:
            return jsonify({"error": "Video not found"}), 404
    return send_file(
        video_path,
        mimetype="video/mp4",
        conditional=True,
    )


@app.route("/api/captcha/validate", methods=["POST"])
@require_api_key
def ext_validate_captcha():
    data   = request.get_json() or {}
    token  = data.get("token", "")
    answer = data.get("answer", "")

    if not token or not answer:
        return jsonify({"success": False, "error": "token and answer required"}), 400

    is_correct, message = db.verify_captcha(token, answer)

    try:
        vp = os.path.join(captcha_gen.output_dir, f"{token}.mp4")
        if os.path.exists(vp):
            os.remove(vp)
    except Exception:
        pass

    return jsonify({"success": is_correct, "message": message})


# ── Public widget script endpoint ─────────────────────────────────────────────

@app.route("/widget.js")
def serve_widget():
    widget_path = os.path.join(os.path.dirname(__file__), "widget.js")
    if os.path.exists(widget_path):
        return send_file(widget_path, mimetype="application/javascript")
    return "// widget.js not found", 404


# ═════════════════════════════════════════════════════════════════════════════
# ── INTERNAL ROUTES  (used by the React dashboard frontend)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/generate", methods=["GET"])
def generate_captcha():
    """
    Internal generate endpoint with 3-second timeout → cached-video fallback.
    """
    try:
        db.cleanup_expired_captchas()

        captcha_data = None
        from_cache   = False

        # ── Try live generation (3 s budget) ──────────────────────────────
        try:
            captcha_data = _generate_with_timeout(db)
            logger.info(f"✅ Live generation succeeded: {captcha_data['captcha_id']}")
        except concurrent.futures.TimeoutError:
            logger.warning(
                f"⏱  Live CAPTCHA generation exceeded {GENERATION_TIMEOUT_SEC}s — "
                f"falling back to cached video"
            )
            captcha_data = _serve_cached_fallback()
            from_cache   = True
        except Exception as exc:
            logger.warning(f"Live generation error ({exc}) — falling back to cache")
            captcha_data = _serve_cached_fallback()
            from_cache   = True

        if not captcha_data:
            return jsonify({
                "success": False,
                "error":   "Failed to generate CAPTCHA and no cached videos available"
            }), 500

        db.store_captcha(
            captcha_data["captcha_id"],
            captcha_data["correct_answer"],
            captcha_data["question"],
            expiry_minutes=config.CAPTCHA_EXPIRY_MINUTES,
        )

        return jsonify({
            "success":      True,
            "video_url":    f"/api/video/{captcha_data['captcha_id']}",
            "question":     captcha_data["question"],
            "token":        captcha_data["captcha_id"],
            "from_cache":   from_cache,
            "ai_tested":    True,
            "ai_resistant": True,
        })

    except Exception as exc:
        logger.error(f"generate_captcha unexpected error: {exc}")
        return jsonify({"success": False, "error": "Unexpected server error"}), 500


@app.route("/api/video/<captcha_id>")
def serve_video(captcha_id):
    video_path = os.path.join(captcha_gen.output_dir, f"{captcha_id}.mp4")
    if not os.path.exists(video_path):
        raw_path = os.path.join(captcha_gen.output_dir, f"{captcha_id}_raw.mp4")
        if os.path.exists(raw_path):
            video_path = raw_path
        else:
            return jsonify({"error": "Video not found"}), 404
    return send_file(video_path, mimetype="video/mp4", conditional=True)


@app.route("/api/validate", methods=["POST"])
def validate_captcha():
    data   = request.get_json() or {}
    token  = data.get("token", "")
    answer = data.get("answer", "")

    if not token or not answer:
        return jsonify({"success": False, "error": "Missing token or answer"}), 400

    is_correct, message = db.verify_captcha(token, answer)

    try:
        vp = os.path.join(captcha_gen.output_dir, f"{token}.mp4")
        if os.path.exists(vp):
            os.remove(vp)
    except Exception:
        pass

    return jsonify({"success": is_correct, "message": message})


@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        return jsonify({"success": True, "stats": db.get_stats()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    ok, msg = db.test_connection()
    return jsonify({
        "status":   "healthy" if ok else "unhealthy",
        "message":  "VideoCap API running",
        "database": {"connected": ok, "message": msg},
    })


@app.route("/api/generation_stats", methods=["GET"])
def get_generation_stats():
    try:
        return jsonify({"success": True, "stats": captcha_gen.get_generation_stats()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    os.makedirs(config.BASE_VIDEOS_DIR, exist_ok=True)
    os.makedirs(config.OUTPUT_DIR,      exist_ok=True)

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  VideoCap API server starting")
    logger.info(f"  Generation timeout: {GENERATION_TIMEOUT_SEC}s (falls back to cache)")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  Third-party integration endpoints:")
    logger.info("    GET  /api/captcha/generate   (X-API-Key required)")
    logger.info("    POST /api/captcha/validate   (X-API-Key required)")
    logger.info("    GET  /api/captcha/video/<id> (X-API-Key required)")
    logger.info("  Key management:")
    logger.info("    POST /api/keys/create")
    logger.info("    GET  /api/keys?email=...")
    logger.info("    POST /api/keys/<id>/revoke")
    logger.info("    POST /api/keys/<id>/domains")
    logger.info("  Internal (React frontend):")
    logger.info("    GET  /api/generate")
    logger.info("    POST /api/validate")
    logger.info("    GET  /api/video/<id>")
    logger.info("    GET  /api/health | /api/stats")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT, use_reloader=False)