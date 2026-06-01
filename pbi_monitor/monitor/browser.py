import os
import shutil
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_chrome_user_data_dir():
    # Detects if running on Windows (Local) or Linux (Render)
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return os.path.join(local_app_data, "Google", "Chrome", "User Data")
    # Fallback path for Linux/Render environment
    return os.path.expanduser("~/.config/google-chrome")

def copy_profile_to_temp():
    src_profile = os.path.join(get_chrome_user_data_dir(), "Default")
    tmp_dir = tempfile.mkdtemp(prefix="pbi_monitor_chrome_")
    dst_profile = os.path.join(tmp_dir, "Default")

    # If local profile doesn't exist (like on Render), skip copying files
    if not os.path.exists(src_profile):
        print(f"[browser] No existing profile found at {src_profile}. Starting fresh.")
        return tmp_dir

    os.makedirs(dst_profile, exist_ok=True)

    essential = [
        "Cookies",
        "Login Data",
        "Web Data",
        "Preferences",
        "Secure Preferences",
        "Local Storage",
        "Session Storage",
        "Network",
    ]

    for item in essential:
        src = os.path.join(src_profile, item)
        dst = os.path.join(dst_profile, item)
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            elif os.path.isfile(src):
                shutil.copy2(src, dst)
        except Exception:
            pass  # Skip locked or missing files silently

    print(f"[browser] Temp profile created at: {tmp_dir}")
    return tmp_dir

def create_driver(headless: bool = True): # Must be True on Render
    opts = Options()

    tmp_dir = copy_profile_to_temp()
    opts.add_argument(f"--user-data-dir={tmp_dir}")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-extensions")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # Render forces headless mode because it lacks a display GUI
    if headless or os.environ.get("RENDER"):
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        
    # Render environment check for Chrome location
    if os.environ.get("RENDER"):
        # Points to the Chrome binary we will install via build script
        opts.binary_location = "/opt/render/project/src/.render/chrome/chrome-linux64/chrome"
        driver = webdriver.Chrome(options=opts)
    else:
        # Local development auto-downloads the correct driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)

    driver.set_page_load_timeout(60)
    driver._tmp_profile_dir = tmp_dir
    return driver
