import os
import sys
import shutil
import tempfile
import json
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.core.driver_cache import DriverCacheManager


def get_edge_user_data_dir():
    """Returns the Edge user data directory for the current Windows user."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return os.path.join(local_app_data, "Microsoft", "Edge", "User Data")
    return os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data")


def get_active_edge_profile():
    """Finds whichever Edge profile was last used. Falls back to Default."""
    user_data_dir = get_edge_user_data_dir()
    local_state_path = os.path.join(user_data_dir, "Local State")
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.load(f)
        return local_state.get("profile", {}).get("last_used", "Default")
    except Exception:
        return "Default"


def copy_profile_to_temp():
    """
    Copies only auth-related files from the Edge profile to a temp folder.
    This lets Selenium open Edge independently without touching the real profile
    and without causing lockfile conflicts when Edge is already open.
    """
    profile = get_active_edge_profile()
    src_profile = os.path.join(get_edge_user_data_dir(), profile)
    tmp_dir = tempfile.mkdtemp(prefix="pbi_monitor_edge_")
    dst_profile = os.path.join(tmp_dir, profile)

    os.makedirs(dst_profile, exist_ok=True)

    essential = [
        "Cookies",
        "Login Data",
        "Login Data For Account",
        "Web Data",
        "Preferences",
        "Secure Preferences",
        "Local Storage",
        "Session Storage",
        "Network",
        "Extension State",
        "Sync Data",
        "Edge Wallet",
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
            pass  # skip locked files silently

    print(f"[browser] Temp profile created at: {tmp_dir}")
    return tmp_dir, profile


def get_driver_cache_path():
    """Returns writable cache path for EdgeDriver when running as .exe."""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), ".wdm")
    return None


def create_driver(headless: bool = False):
    opts = Options()

    tmp_dir, profile = copy_profile_to_temp()
    print(f"[browser] Using Edge profile: {profile}")

    opts.add_argument(f"--user-data-dir={tmp_dir}")
    opts.add_argument(f"--profile-directory={profile}")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-extensions")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")

    cache_path = get_driver_cache_path()
    if cache_path:
        manager = EdgeChromiumDriverManager(
            cache_manager=DriverCacheManager(cache_path)
        )
    else:
        manager = EdgeChromiumDriverManager()

    service = Service(manager.install())
    driver = webdriver.Edge(service=service, options=opts)
    driver.set_page_load_timeout(60)
    driver._tmp_profile_dir = tmp_dir
    return driver