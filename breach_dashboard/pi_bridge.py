#!/usr/bin/env python3
"""
pi_bridge.py — Local HTTP bridge between Prospector dashboard and Pi coding agent.

Runs a small Flask server on http://localhost:5050.
Pi is invoked in print mode (-p flag) for non-interactive single-shot use.

SETUP (one time):
    1. Install Pi:
       npm install -g @mariozechner/pi-coding-agent

    2. Configure Ollama as a Pi provider (pi_bridge.py will do this automatically
       on first run, or you can run: python pi_bridge.py --setup)

    3. Install pip dependencies:
       pip install flask flask-cors

    4. Start Ollama with CORS:
       $env:OLLAMA_ORIGINS="*"; ollama serve

    5. Start this bridge:
       python pi_bridge.py

Usage:
    python pi_bridge.py           # start the bridge server
    python pi_bridge.py --setup   # just write Pi config and exit
"""

import subprocess
import json
import sys
import shutil
import os
import re
import argparse
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

app    = Flask(__name__)
CORS(app)

# ── CONFIGURATION ────────────────────────────────────────────────────────────
BRIDGE_PORT   = 5050
DEFAULT_MODEL = "mistral"
OLLAMA_BASE   = "http://localhost:11434"
PI_TIMEOUT    = 120   # seconds — increased from 45; LLM inference takes time


# ── FIND PI ──────────────────────────────────────────────────────────────────
def find_pi():
    """Return the path to the pi executable, or None if not found."""
    found = shutil.which("pi")
    if found:
        return found
    for candidate in [
        os.path.expandvars(r"%APPDATA%\npm\pi.cmd"),
        os.path.expandvars(r"%APPDATA%\npm\pi"),
        os.path.expandvars(r"%ProgramFiles%\nodejs\pi.cmd"),
    ]:
        if os.path.exists(candidate):
            return candidate
    # nvm4w location
    nvm_nodejs = r"C:\nvm4w\nodejs\pi.CMD"
    if os.path.exists(nvm_nodejs):
        return nvm_nodejs
    return None


# ── SETUP PI OLLAMA CONFIG ────────────────────────────────────────────────────
PI_CONFIG_DIR = Path.home() / ".pi" / "agent"
MODELS_JSON   = PI_CONFIG_DIR / "models.json"
SETTINGS_JSON = PI_CONFIG_DIR / "settings.json"

def setup_pi_ollama_config(model_id=DEFAULT_MODEL):
    """Write ~/.pi/agent/models.json and settings.json to configure Ollama."""
    PI_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if MODELS_JSON.exists():
        try:
            existing = json.loads(MODELS_JSON.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    else:
        existing = {}

    providers = existing.get("providers", {})
    providers["ollama"] = {
        "baseUrl": f"{OLLAMA_BASE}/v1",
        "api":     "openai-completions",
        "apiKey":  "ollama",
        "compat": {
            "supportsDeveloperRole":   False,
            "supportsReasoningEffort": False
        },
        "models": [{"id": model_id}]
    }
    existing["providers"] = providers
    MODELS_JSON.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    if SETTINGS_JSON.exists():
        try:
            settings = json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
        except Exception:
            settings = {}
    else:
        settings = {}

    settings["defaultProvider"] = "ollama"
    settings["defaultModel"]    = model_id
    SETTINGS_JSON.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    print(f"  ✓ Pi config written to {PI_CONFIG_DIR}")
    print(f"    models.json   → Ollama provider with model: {model_id}")
    print(f"    settings.json → defaultProvider: ollama, defaultModel: {model_id}")


# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    pi_path = find_pi()
    if not pi_path:
        return jsonify({
            "status":  "error",
            "message": "Pi not found. Run: npm install -g @mariozechner/pi-coding-agent"
        }), 503
    return jsonify({
        "status":        "ok",
        "pi_path":       pi_path,
        "config":        str(MODELS_JSON),
        "config_exists": MODELS_JSON.exists(),
    })


@app.route("/setup", methods=["POST"])
def setup_route():
    data     = request.get_json(force=True) or {}
    model_id = data.get("model", DEFAULT_MODEL)
    try:
        setup_pi_ollama_config(model_id)
        return jsonify({"status": "ok", "message": f"Pi configured for Ollama with model {model_id}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/enrich", methods=["POST"])
def enrich():
    """
    Enrich a single company using Pi (no web tools — pure LLM inference).

    Request JSON:
    {
        "company":  "CareCloud",
        "website":  "https://carecloud.com",
        "model":    "mistral",
        "context":  "optional breach summary"
    }

    Response JSON:
    {
        "emails_general":  "...",
        "emails_security": "...",
        "emails_staff":    "...",
        "email_patterns":  "...",
        "phones":          "...",
        "addresses":       "...",
        "raw":             "full Pi output"
    }
    """
    data    = request.get_json(force=True)
    company = data.get("company", "").strip()
    website = data.get("website", "").strip()
    model   = data.get("model",   DEFAULT_MODEL).strip()
    context = data.get("context", "").strip()

    if not company:
        return jsonify({"error": "company field is required"}), 400

    pi_path = find_pi()
    if not pi_path:
        return jsonify({"error": "Pi not found. Run: npm install -g @mariozechner/pi-coding-agent"}), 503

    if not MODELS_JSON.exists():
        setup_pi_ollama_config(model)

    prompt = (
        "You are a data extraction engine.\n"
        "Extract ALL contact emails from the following company:\n\n"
        f"Company: {company}\n"
        + (f"Website: {website}\n" if website else "")
        + (f"Context: {context}\n" if context else "")
        + "\n\n"
        "IMPORTANT:\n"
        "- Do NOT browse the internet\n"
        "- Do NOT use tools\n"
        "- Only return known or pattern-based emails\n"
        "- If a common email pattern applies (e.g. firstname.lastname@company.com), include it\n"
        "\nReturn ONLY a valid JSON object with no other text, no markdown, no explanation:\n"
        '{"emails_general":"comma-separated general contact emails or empty string",'
        '"emails_security":"comma-separated security/abuse emails or empty string",'
        '"emails_staff":"comma-separated known staff emails or empty string",'
        '"email_patterns":"common email format pattern e.g. {first}.{last}@domain.com or empty string",'
        '"phones":"comma-separated US phone numbers or empty string",'
        '"addresses":"comma-separated physical addresses or empty string"}'
    )

    cmd = [pi_path, "-p", prompt, "--provider", "ollama", "--model", model]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PI_TIMEOUT,
            encoding="utf-8",
            errors="replace",
        )

        raw    = result.stdout.strip()
        stderr = result.stderr.strip()

        if stderr:
            print(f"\n=== Pi STDERR ({company}) ===\n{stderr[:400]}\n============================\n")

        if result.returncode != 0 and not raw:
            return jsonify({
                "error":  f"Pi exited with code {result.returncode}",
                "stderr": stderr[:500],
                "raw":    raw,
            }), 500

        parsed = extract_json(raw)
        if parsed:
            return jsonify({
                "emails_general":  parsed.get("emails_general",  ""),
                "emails_security": parsed.get("emails_security", ""),
                "emails_staff":    parsed.get("emails_staff",    ""),
                "email_patterns":  parsed.get("email_patterns",  ""),
                "phones":          parsed.get("phones",          ""),
                "addresses":       parsed.get("addresses",       ""),
                "raw":             raw,
            })
        else:
            return jsonify({
                "emails_general":  "",
                "emails_security": "",
                "emails_staff":    "",
                "email_patterns":  "",
                "phones":          "",
                "addresses":       "",
                "raw":             raw,
                "warning":         "Pi responded but JSON could not be extracted from output",
            })

    except subprocess.TimeoutExpired:
        return jsonify({"error": f"Pi timed out after {PI_TIMEOUT} seconds"}), 504
    except FileNotFoundError:
        return jsonify({"error": f"Pi executable not found at: {pi_path}"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/models", methods=["GET"])
def list_models():
    import urllib.request
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=5) as resp:
            data   = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            return jsonify({"models": models})
    except Exception as e:
        return jsonify({"models": [], "error": str(e)})


# ── HELPERS ───────────────────────────────────────────────────────────────────
def extract_json(text):
    """
    Extract the first valid JSON object from Pi's output.
    Uses a greedy match to handle nested content correctly.
    """
    # Direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass

    # Strip markdown code fences if present
    cleaned = re.sub(r'```(?:json)?\s*', '', text).replace('```', '').strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Greedy match for outermost JSON object — handles nested braces
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return None


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prospector Pi Bridge Server")
    parser.add_argument("--setup", action="store_true", help="Write Pi Ollama config and exit")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Default Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--port",  type=int, default=BRIDGE_PORT, help=f"Port to listen on (default: {BRIDGE_PORT})")
    args = parser.parse_args()

    print("\n  Prospector — Pi Bridge Server")
    print("  ─────────────────────────────────────────")

    if args.setup:
        print(f"\n  Writing Pi config for Ollama (model: {args.model})...")
        setup_pi_ollama_config(args.model)
        print("\n  Done. Now start the bridge with: python pi_bridge.py")
        sys.exit(0)

    pi_path = find_pi()
    if pi_path:
        print(f"  ✓ Pi found:    {pi_path}")
    else:
        print("  ✗ Pi NOT found. Install with:")
        print("    npm install -g @mariozechner/pi-coding-agent")

    if not MODELS_JSON.exists():
        print(f"\n  Pi Ollama config not found — writing it now...")
        setup_pi_ollama_config(args.model)
    else:
        print(f"  ✓ Pi config:   {MODELS_JSON}")

    print(f"\n  Bridge listening on http://localhost:{args.port}")
    print("  Open Prospector dashboard → use the Pi Enrichment panel.")
    print("  Press Ctrl+C to stop.\n")

    app.run(host="127.0.0.1", port=args.port, debug=False)