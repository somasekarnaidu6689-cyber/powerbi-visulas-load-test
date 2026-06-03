# Power BI Visual Health Monitor

## Overview

This repository contains a Power BI visual health monitor built with Python, Flask, Selenium, and Microsoft Edge WebDriver. The application loads Power BI report URLs, navigates report pages, waits for visuals to render, detects error conditions, and captures screenshots for analysis.

The project includes a small web interface for entering a report URL, starting a scan, and viewing scan progress and results.

## Architecture

The project is organized into two main areas:

- `pbi_monitor/`: the application and monitoring logic
- `powerBiFiles/`: sample Power BI report files and model packages for load testing or development reference

Within `pbi_monitor/`:

- `app.py`: defines the Flask web server, REST endpoints, scan state management, and the scan control loop. It uses threading so scans run in the background while the web interface remains responsive.
- `monitor/browser.py`: creates a Selenium Edge browser instance with a copied Edge user profile. It manages Edge WebDriver installation, temporary profile creation, and browser startup options.
- `monitor/scanner.py`: contains the core scanning logic. It loads a Power BI report URL, detects report pages or tabs, waits for page load, waits for visuals to fully render, scans for visible errors, and saves screenshots.
- `templates/index.html`: the web UI for interacting with the monitor. It is served by Flask from `app.py`.
- `requirements.txt`: lists the Python dependencies needed to run the app.

## How the scan works

1. The user submits a Power BI report URL through the web interface.
2. `app.py` starts a new background thread and calls `run_scan(url)`.
3. `browser.py` creates a Selenium Edge driver using a temporary copy of the current user Edge profile.
4. `scanner.py` opens the URL in the browser and waits for the report page to load.
5. The scanner finds report page tabs or falls back to scanning the current page.
6. For each page, the scanner waits for visuals to load and remain stable, then checks for common Power BI error selectors.
7. The scanner saves a screenshot of each page and returns a result summary.

## Key files and functions

- `pbi_monitor/app.py`
  - `get_base_path()`: resolves path for running as a normal Python script or as a PyInstaller executable.
  - `get_runtime_path()`: returns the path for writable runtime artifacts such as screenshots.
  - `run_scan(url)`: main control function for executing a scan in a background thread.
  - `start_scan()`: Flask endpoint that accepts report URLs and starts scanning.
  - `scan_status()`: Flask endpoint that returns current scan progress and results.

- `pbi_monitor/monitor/browser.py`
  - `get_edge_user_data_dir()`: finds the Windows Edge user data folder.
  - `get_active_edge_profile()`: reads the last active Edge profile name.
  - `copy_profile_to_temp()`: copies essential profile files into a temporary folder for Selenium use.
  - `create_driver(headless=False)`: starts Edge WebDriver with the copied profile.

- `pbi_monitor/monitor/scanner.py`
  - `wait_for_report_load(driver, timeout)`: waits until the browser document is fully loaded.
  - `wait_for_page_navigation(driver, timeout)`: detects Power BI page navigation controls.
  - `detect_page_tabs(driver)`: discovers report page tabs or navigation links.
  - `wait_for_visuals_to_load(driver, timeout)`: waits until visuals render and spinners disappear.
  - `scan_for_errors(driver)`: inspects the page for Power BI error messages and visual faults.
  - `take_screenshot(driver, page_name, status)`: saves a screenshot for each scanned page.
  - `scan_report(driver, url, log_callback)`: orchestrates report scanning and returns page-level results.

## Use cases and implementable workflows

1. Add automation inside Excel to push scan results into a new row every time a report gets analyzed.
   - Use Excel scripting or Office Scripts to call the monitor API or consume exported result files.
   - Append timestamp, report URL, report status, error summary, and screenshot paths to a tracking worksheet.

2. Automate the process with cron-style scheduling from Python.
   - Use `schedule`, `APScheduler`, or operating system task scheduler to trigger scans periodically.
   - Create a Python script that reads a list of Power BI report URLs and sends them to the Flask endpoint.

3. Create a JSON file of different report URLs and automate scanning them one by one.
   - Use a JSON list of report metadata, including report name, URL, and owner.
   - Run a loop that iterates through the list, calls the scan API, and logs or exports the results.

4. Send notifications when a scan detects an error or timeout.
   - Integrate with email, Microsoft Teams, Slack, or another alerting channel.
   - Trigger alerts only when scan results indicate `page_status` of `error` or `timeout`.

5. Build a periodic reporting dashboard from scan history.
   - Store scan summaries in a database, CSV file, or Excel workbook.
   - Generate weekly or monthly reports of report availability, error frequency, and page load stability.

6. Use the monitor as part of a Power BI deployment validation pipeline.
   - After deploying or updating a report, automatically scan the published report URL.
   - Fail the pipeline or record deployment issues if errors are detected.

## Running the project

1. Install Python dependencies:
   ```bash
   pip install -r pbi_monitor/requirements.txt
   ```
2. Start the Flask server from the `pbi_monitor` folder:
   ```bash
   python app.py
   ```
3. Open the web interface at `http://localhost:5000`.
4. Enter a Power BI report URL and start the scan.

## Notes

- The project currently uses Microsoft Edge and Selenium to interact with the report page.
- The browser profile is copied to a temporary directory to avoid interfering with the live Edge session.
- Screenshots are saved to `pbi_monitor/screenshots`.
- The sample Power BI files in `powerBiFiles/` are included for reference and are not required to run the Flask monitor.
