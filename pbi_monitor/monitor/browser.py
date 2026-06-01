import os
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def get_chrome_binary():
    candidates = [
        os.environ.get("CHROME_BINARY"),
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def create_driver(headless: bool = True):
    opts = Options()
    chrome_binary = get_chrome_binary()
    if chrome_binary:
        opts.binary_location = chrome_binary

    tmp_dir = os.environ.get("CHROME_USER_DATA_DIR") or tempfile.mkdtemp(prefix="pbi_monitor_chrome_")
    opts.add_argument(f"--user-data-dir={tmp_dir}")
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

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(60)
    driver._tmp_profile_dir = tmp_dir
    return driver