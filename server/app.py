import threading
import time
from typing import Optional, Dict
from pathlib import Path
import webbrowser

from flask import Flask, request, jsonify, send_from_directory, send_file, abort
from flask_cors import CORS

# Speech recognition and translation libraries
import speech_recognition as sr  # type: ignore
from deep_translator import GoogleTranslator

# ------------------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------------------

# Assume project layout:
# project-root/
#   index.html          <-- frontend
#   server/
#     app.py            <-- this file
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT
INDEX_FILE = FRONTEND_DIR / "index.html"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins for local dev

# ------------------------------------------------------------------------------
# Global state (thread-safe)
# ------------------------------------------------------------------------------
state_lock = threading.Lock()
state: Dict[str, Optional[object]] = {
    "running": False,
    "thread": None,
    "stop_event": None,
    "translated_text": "Waiting for speech...",
    "source_lang": None,
    "target_lang": None,
}

# ------------------------------------------------------------------------------
# Language mapping helpers
# ------------------------------------------------------------------------------
SR_LANG_MAP = {
    # Source language (UI) -> Google Speech Recognition locale
    "en": "en-US",
    "hi": "hi-IN",
    "gu": "gu-IN",
    "cn": "zh-CN",
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-CN": "zh-CN",
    "ko": "ko-KR",
}

TR_LANG_MAP = {
    # Frontend code -> deep-translator GoogleTranslator code
    "en": "en",
    "hi": "hi",
    "gu": "gu",
    "cn": "zh-CN",
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-CN": "zh-CN",
    "ko": "ko",
}


def normalize_sr_lang(code: str) -> str:
    c = (code or "").strip()
    return SR_LANG_MAP.get(c, SR_LANG_MAP.get(c.lower(), "en-US"))


def normalize_tr_lang(code: str) -> str:
    c = (code or "").strip()
    return TR_LANG_MAP.get(c, TR_LANG_MAP.get(c.lower(), "en"))


# ------------------------------------------------------------------------------
# Background worker
# ------------------------------------------------------------------------------
def listen_and_translate(source_lang: str, target_lang: str, stop_event: threading.Event):
    """
    Background worker that listens to microphone audio, performs speech recognition,
    translates the recognized text, and updates state["translated_text"].
    """
    recognizer = sr.Recognizer()

    # Create microphone inside the thread to avoid device handle issues across threads
    try:
        mic = sr.Microphone()
    except Exception as e:
        with state_lock:
            state["translated_text"] = f"Microphone error: {e}"
            state["running"] = False
            state["thread"] = None
            state["stop_event"] = None
        return

    sr_locale = normalize_sr_lang(source_lang)
    tr_source = normalize_tr_lang(source_lang)
    tr_target = normalize_tr_lang(target_lang)

    # Ambient noise calibration
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
    except Exception as e:
        with state_lock:
            state["translated_text"] = f"Audio initialization error: {e}"
            state["running"] = False
            state["thread"] = None
            state["stop_event"] = None
        return

    with state_lock:
        state["translated_text"] = f"Listening... (SR: {sr_locale}, TR: {tr_source} -> {tr_target})"

    while not stop_event.is_set():
        try:
            with mic as source:
                # timeout lets us periodically check stop_event
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=7)
        except sr.WaitTimeoutError:
            continue
        except Exception as e:
            with state_lock:
                state["translated_text"] = f"Mic capture error: {e}"
            time.sleep(0.3)
            continue

        # Recognize speech
        try:
            transcript = recognizer.recognize_google(audio, language=sr_locale)
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            with state_lock:
                state["translated_text"] = f"Speech recognition API error: {e}"
            time.sleep(1.0)
            continue
        except Exception as e:
            with state_lock:
                state["translated_text"] = f"Unexpected SR error: {e}"
            time.sleep(0.5)
            continue

        if not transcript:
            continue

        # Translate
        try:
            try:
                translated = GoogleTranslator(source=tr_source, target=tr_target).translate(transcript)
            except Exception:
                translated = GoogleTranslator(source="auto", target=tr_target).translate(transcript)
        except Exception as e:
            translated = f"{transcript} (translation unavailable: {e})"

        with state_lock:
            state["translated_text"] = translated

        time.sleep(0.05)

    # Clean exit
    with state_lock:
        state["running"] = False
        state["thread"] = None
        state["stop_event"] = None
        if not state["translated_text"]:
            state["translated_text"] = "Stopped."


# ------------------------------------------------------------------------------
# API routes
# ------------------------------------------------------------------------------
@app.route("/start", methods=["POST"])
def start():
    data = request.get_json(silent=True) or {}
    source_lang = data.get("sourceLang", "en")
    target_lang = data.get("targetLang", "en")

    with state_lock:
        if state["running"]:
            return jsonify({"message": "Already running", "translatedText": state["translated_text"]}), 200

        stop_event = threading.Event()
        worker = threading.Thread(
            target=listen_and_translate,
            args=(source_lang, target_lang, stop_event),
            daemon=True,
        )
        state["running"] = True
        state["thread"] = worker
        state["stop_event"] = stop_event
        state["source_lang"] = source_lang
        state["target_lang"] = target_lang
        state["translated_text"] = "Starting speech recognition..."

        worker.start()

    return jsonify({"message": "Listening and translating...", "translatedText": state["translated_text"]}), 200


@app.route("/stop", methods=["GET"])
def stop():
    with state_lock:
        if not state["running"]:
            return jsonify({"message": "Not running"}), 200
        stop_event: threading.Event = state["stop_event"]
        worker: threading.Thread = state["thread"]

    if stop_event:
        stop_event.set()

    if worker and worker.is_alive():
        worker.join(timeout=5)

    with state_lock:
        state["running"] = False
        state["thread"] = None
        state["stop_event"] = None
        state["translated_text"] = "Stopped."

    return jsonify({"message": "Stopped."}), 200


@app.route("/status", methods=["GET"])
def status():
    with state_lock:
        return jsonify({
            "running": state["running"],
            "translatedText": state["translated_text"],
            "sourceLang": state["source_lang"],
            "targetLang": state["target_lang"],
        }), 200


# ------------------------------------------------------------------------------
# Frontend routes (serve index.html and common static assets)
# ------------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def serve_index():
    if INDEX_FILE.exists():
        return send_file(INDEX_FILE)
    return "index.html not found next to project root", 404


# Serve common static files (css/js/images) from the project root.
# This avoids interfering with API endpoints (/start, /stop, /status).
ALLOWED_STATIC_EXTS = {
    ".css", ".js", ".mjs", ".map",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".woff", ".woff2", ".ttf", ".otf",
}

@app.route("/<path:filename>", methods=["GET"])
def serve_static_file(filename: str):
    # Don't let this route handle API paths
    if filename in {"start", "stop", "status"}:
        return abort(404)

    target = (FRONTEND_DIR / filename).resolve()
    # Security: ensure path stays within FRONTEND_DIR
    try:
        target.relative_to(FRONTEND_DIR)
    except ValueError:
        return abort(403)

    if target.is_file() and target.suffix in ALLOWED_STATIC_EXTS:
        return send_from_directory(FRONTEND_DIR, filename)

    return abort(404)


# ------------------------------------------------------------------------------
# Entrypoint (auto-open browser)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Auto-open the index page in the default browser shortly after server starts
    host = "127.0.0.1"  # use localhost for the browser URL
    port = 5000
    threading.Timer(0.8, lambda: webbrowser.open(f"http://{host}:{port}/")).start()
    # Bind to all interfaces so other devices can hit it if needed
    app.run(host="0.0.0.0", port=port, debug=True)
