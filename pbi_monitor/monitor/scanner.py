import time
import os
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys

def get_runtime_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__ + "/.."))

SCREENSHOTS_DIR = os.path.join(get_runtime_path(), "screenshots")

ERROR_SELECTORS = [
    "div.errorMessage.themableBackgroundColorSolid",
    "[class*='errorMessage']",
    "div.pbi-glyph-error",
    "a[data-testid='see_detail.link']",
    ".visualError",
    ".visual-error",
    "[class*='visualWarning']",
    ".no-data-message",
]

PAGE_TAB_SELECTORS = [
    # Most specific — Power BI page nav strip at the bottom
    "[aria-label='Page Navigation'] [role='tab']",
    "[aria-label='Page navigation'] [role='tab']",
    ".reportPageNavigationStrip [role='tab']",
    "[class*='pageNavigationStrip'] [role='tab']",
    "[class*='pageNavigation'] [role='tab']",

    # New canvas sidebar navigation structure
    "app-navigation-list app-navigation-list [data-testid='item-row'][role='link']",
    "app-navigation-list [data-testid='item-row'][role='link']",

    # Fallback — any tab with a visible name that isn't a toolbar button
    "[role='tablist'] [role='tab']",
]


def detect_page_tabs(driver):
    driver.switch_to.default_content()

    for selector in PAGE_TAB_SELECTORS:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if not elements:
            continue

        tabs = []
        for el in elements:
            name = (
                el.get_attribute("title")
                or el.get_attribute("aria-label")
                or el.text.strip()
            )
            # Filter out toolbar buttons — real page tabs have short plain names
            # Toolbar items tend to be icon-only or have tooltip-style names
            if not name or len(name.strip()) == 0:
                continue
            if name.strip().lower() in ["fit to page", "fit to width", "actual size",
                                         "full screen", "zoom in", "zoom out",
                                         "reset", "bookmark", "filter", "more options"]:
                continue

            tabs.append((name.strip(), el))

        if tabs:
            seen, unique = set(), []
            for name, el in tabs:
                if name not in seen:
                    seen.add(name)
                    unique.append((name, el))
            print(f"[debug] Detected tabs with selector '{selector}':")
            for name, el in unique:
                print(f"  - '{name}' | aria-selected={el.get_attribute('aria-selected')} | class={el.get_attribute('class')[:60]}")
            return unique

    return []


def wait_for_report_load(driver, timeout=45):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(5)

def wait_for_visuals_to_load(driver, timeout=120):
    """
    Wait for Power BI visuals to stabilize.
    Avoids infinite waiting caused by hidden loading elements.
    """

    start = time.time()

    stable_required = 5
    stable_since = None

    previous_rendered = -1

    while time.time() - start < timeout:

        try:
            state = driver.execute_script("""
                const result = {
                    visuals: 0,
                    rendered: 0,
                    visibleSpinners: 0,
                    errors: 0
                };

                // Count actual visible visuals
                const visuals = document.querySelectorAll(
                    '.visualContainer, [class*="visual"]'
                );

                result.visuals = visuals.length;

                visuals.forEach(v => {

                    const visible =
                        v.offsetWidth > 30 &&
                        v.offsetHeight > 30;

                    if (visible) {
                        result.rendered++;
                    }

                    // Detect visible spinner INSIDE visual
                    const spinner = v.querySelector(
                        '.spinner, .loadingIndicator, .pbi-glyph-load'
                    );

                    if (
                        spinner &&
                        spinner.offsetParent !== null
                    ) {
                        result.visibleSpinners++;
                    }

                    // Detect errors
                    const err =
                        v.querySelector('[class*="error"]') ||
                        v.querySelector('.visual-error') ||
                        v.querySelector('.pbi-glyph-error');

                    if (err) {
                        result.errors++;
                    }
                });

                return result;
            """)

            print(
                f"[debug] visuals={state['visuals']} "
                f"rendered={state['rendered']} "
                f"spinners={state['visibleSpinners']} "
                f"errors={state['errors']}"
            )

            rendered = state["rendered"]

            # Main readiness condition
            ready = (
                rendered > 0 and
                state["visibleSpinners"] == 0
            )

            # Detect stabilization
            if ready:

                if rendered == previous_rendered:

                    if stable_since is None:
                        stable_since = time.time()

                    stable_time = time.time() - stable_since

                    if stable_time >= stable_required:
                        print("[debug] visuals stabilized")
                        return True

                else:
                    stable_since = None

            else:
                stable_since = None

            previous_rendered = rendered

        except Exception as e:
            print(f"[debug] wait error: {e}")

        time.sleep(1)

    print(f"[warning] visuals did not stabilize within {timeout}s")
    return False

def switch_into_report_iframe(driver):
    driver.switch_to.default_content()
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if not iframes:
        return False
    for iframe in iframes:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            body = driver.execute_script("return document.body ? document.body.innerHTML : '';")
            if any(kw in body for kw in ["reportPage", "visual", "pbi-", "errorMessage"]):
                return True
        except Exception:
            continue
    driver.switch_to.default_content()
    try:
        driver.switch_to.frame(iframes[0])
        return True
    except Exception:
        return False


def scan_for_errors(driver):
    errors = []
    seen = set()
    for selector in ERROR_SELECTORS:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, selector):
                if el.id in seen:
                    continue
                seen.add(el.id)
                text = driver.execute_script(
                    """
                    const el = arguments[0];
                    const root = el.closest('[class*=errorMessage]') || el;
                    const span = root.querySelector('[class*=errorSpan]');
                    return (span ? span.textContent : el.textContent).trim();
                    """,
                    el
                ) or "Visual error detected"
                errors.append({"selector": selector, "message": text[:200]})
        except Exception:
            continue
    return errors


def take_screenshot(driver, page_name):
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    safe = "".join(c if c.isalnum() else "_" for c in page_name)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe}_{ts}.png"
    driver.switch_to.default_content()
    driver.save_screenshot(os.path.join(SCREENSHOTS_DIR, filename))
    return filename


def scan_report(driver, url, log_callback):
    results = []

    log_callback("Opening report URL...", "active")
    driver.get(url)

    log_callback("Waiting for report to load...", "active")
    wait_for_report_load(driver)
    log_callback("Report loaded", "ok")

    log_callback("Detecting report pages...", "active")

    detected_tabs = detect_page_tabs(driver)

    if not detected_tabs:
        log_callback("Page tabs not detected — scanning current page only", "active")
        tab_names = ["Page 1"]
    else:
        tab_names = [name for name, _ in detected_tabs]
        log_callback(f"Found {len(tab_names)} page(s)", "ok")

    for page_name in tab_names:

        log_callback(f"Navigating to: {page_name}", "active")

        tab_el = None

        # Re-detect tabs every iteration to avoid stale elements
        current_tabs = detect_page_tabs(driver)

        for name, el in current_tabs:
            if name == page_name:
                tab_el = el
                break

        if tab_el is not None:
            try:
                driver.switch_to.default_content()

                # Scroll into view
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    tab_el
                )

                time.sleep(1)

                # Click tab
                driver.execute_script("arguments[0].click();", tab_el)

                # Wait briefly for page transition
                time.sleep(3)

            except Exception as e:
                log_callback(
                    f"Could not click tab for {page_name}: {e}",
                    "error"
                )

        # Switch into report iframe
        switch_into_report_iframe(driver)

        # WAIT FOR VISUALS
        log_callback(
            f"Waiting for visuals on '{page_name}' to fully load...",
            "active"
        )

        wait_for_visuals_to_load(driver, timeout=120)

        log_callback(
            f"Visual loading complete for '{page_name}'",
            "ok"
        )

        # Scan errors AFTER visuals stabilize
        errors = scan_for_errors(driver)

        has_error = len(errors) > 0

        screenshot = take_screenshot(driver, page_name)

        results.append({
            "page_name": page_name,
            "has_error": has_error,
            "errors": errors,
            "screenshot": screenshot,
        })

        log_callback(
            f"{page_name} — {'ERROR found' if has_error else 'clean'}",
            "error" if has_error else "ok"
        )

    return results