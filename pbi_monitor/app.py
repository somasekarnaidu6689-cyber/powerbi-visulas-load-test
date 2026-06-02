import os
import threading
from flask import Flask, request, jsonify, render_template, send_from_directory
from monitor.browser import create_driver
from monitor.scanner import scan_report
import shutil  
import sys


def get_base_path():
    """Works both when running as .py and as a PyInstaller .exe"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_runtime_path():
    """
    For files that need to be WRITTEN (screenshots, cookies) —
    use the folder where the .exe lives, not the temp bundle folder.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))




app = Flask(__name__, template_folder=os.path.join(get_base_path(), "templates"))
SCREENSHOTS_DIR = os.path.join(get_runtime_path(), "screenshots")

scan_state = {
    "status": "idle",
    "current_step": "",
    "log": [],
    "results": [],
    "message": "",
}


def log(message, state="active"):
    scan_state["log"].append({"message": message, "state": state})
    scan_state["current_step"] = message
    print(f"[{state.upper()}] {message}")




def run_scan(url):
    driver = None
    try:
        scan_state["status"] = "running"
        scan_state["log"] = []
        scan_state["results"] = []
        scan_state["message"] = ""

        log("Launching Chrome with your profile...", "active")
        driver = create_driver(headless=False)

        results = scan_report(driver, url, log)

        scan_state["results"] = results
        scan_state["status"] = "done"
        log("Scan complete", "ok")

    except Exception as e:
        scan_state["status"] = "error"
        scan_state["message"] = str(e)
        log(f"Error: {e}", "error")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
            tmp = getattr(driver, "_tmp_profile_dir", None)
            if tmp and os.path.exists(tmp):
                shutil.rmtree(tmp, ignore_errors=True)
                print(f"[cleanup] Temp profile deleted: {tmp}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start_scan", methods=["POST"])
def start_scan():
    if scan_state["status"] == "running":
        return jsonify({"error": "A scan is already running. Please wait."})
    data = request.get_json()
    url = (data or {}).get("url", "").strip()
    if not url or "powerbi.com" not in url:
        return jsonify({"error": "Please provide a valid Power BI report URL."})
    thread = threading.Thread(target=run_scan, args=(url,), daemon=True)
    thread.start()
    return jsonify({"ok": True})


@app.route("/scan_status")
def scan_status():
    return jsonify(scan_state)


@app.route("/screenshot/<filename>")
def screenshot(filename):
    return send_from_directory(SCREENSHOTS_DIR, filename)
    
if __name__ == "__main__":
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    print("\n  Power BI Visual Health Monitor")
    print("\n  IMPORTANT: Close ALL Chrome windows before starting a scan.\n")
    
    # 1. Fetch the port Render gives you dynamically, defaulting to 5000
    port = int(os.environ.get("PORT", 5000))
    
    # 2. Bind host to 0.0.0.0 so Render can detect and link the port
    app.run(host="0.0.0.0", port=port, debug=False)
