import os
import shutil
import tempfile
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager


def get_edge_user_data_dir():
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return os.path.join(local_app_data, "Microsoft", "Edge", "User Data")
    return os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data")


def copy_profile_to_temp():
    src_profile = os.path.join(get_edge_user_data_dir(), "Default")
    tmp_dir = tempfile.mkdtemp(prefix="pbi_monitor_edge_")
    dst_profile = os.path.join(tmp_dir, "Default")

    os.makedirs(dst_profile, exist_ok=True)

    # Only copy auth-related files — keeps it fast (avoids copying GBs of cache)
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
    return tmp_dir


def create_driver(headless: bool = False):
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

    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")

    service = Service(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=opts)
    driver.set_page_load_timeout(60)
    driver._tmp_profile_dir = tmp_dir
    return driver