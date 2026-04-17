"""
download.py
Logs into Radius and downloads the Digital Workout Plan Report
for the specified month. Returns the local file path.
"""

import json
import os
from datetime import date
from dateutil.relativedelta import relativedelta
from playwright.sync_api import sync_playwright

from config import RADIUS_LOGIN_URL, RADIUS_DWP_URL, INPUT_DIR

# Center IDs: Englewood + Teaneck
CENTER_VALUES = ["2428", "2871"]


def download_dwp_report(data_month: date) -> str:
    """
    Download the Digital Workout Plan report for the given month.
    data_month: first day of the month to download.
    Returns the local path to the downloaded file.
    """
    username = os.environ.get("RADIUS_USERNAME")
    password = os.environ.get("RADIUS_PASSWORD")
    if not username or not password:
        raise EnvironmentError("RADIUS_USERNAME and RADIUS_PASSWORD must be set in the environment.")

    os.makedirs(INPUT_DIR, exist_ok=True)
    output_path = os.path.join(
        INPUT_DIR,
        f"Digital_Workout_Plan_{data_month.strftime('%Y_%m')}.xlsx"
    )

    start = data_month.replace(day=1)
    # Last day of month
    end = (data_month + relativedelta(months=1)) - relativedelta(days=1)

    # Render JS array from CENTER_VALUES constant
    center_values_js = json.dumps(CENTER_VALUES)

    with sync_playwright() as p:
        with p.chromium.launch(headless=True) as browser:
            with browser.new_context(accept_downloads=True) as context:
                page = context.new_page()

                try:
                    print(f"[download] Logging into Radius...")
                    page.goto(RADIUS_LOGIN_URL)
                    page.wait_for_load_state("networkidle")
                    page.fill("#UserName", username)
                    page.fill("#Password", password)
                    page.click("#login")
                    page.wait_for_load_state("networkidle")
                    print("[download] Logged in.")

                    print(f"[download] Navigating to Digital Workout Plan report...")
                    page.goto(RADIUS_DWP_URL)
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2000)

                    # Select both centers via Kendo MultiSelect
                    page.evaluate(f"""
                        var w = jQuery('#AllCenterListMultiSelect').data('kendoMultiSelect');
                        w.value({center_values_js});
                        w.trigger('change');
                    """)
                    page.wait_for_timeout(500)

                    # Set date range via Kendo DatePicker
                    page.evaluate(f"""
                        var startPicker = jQuery('#dwpFromDate').data('kendoDatePicker');
                        startPicker.value('{start.strftime("%m/%d/%Y")}');
                        startPicker.trigger('change');
                        var endPicker = jQuery('#dwpToDate').data('kendoDatePicker');
                        endPicker.value('{end.strftime("%m/%d/%Y")}');
                        endPicker.trigger('change');
                    """)
                    page.wait_for_timeout(500)

                    # Click Search
                    print("[download] Running search...")
                    page.click("#btnsearch")
                    page.wait_for_load_state("networkidle")
                    # Wait for export button to be visible (more reliable than a fixed sleep)
                    page.wait_for_selector("#dwpExcelBtn", state="visible", timeout=30_000)

                    # Download Excel
                    print("[download] Downloading report...")
                    with page.expect_download(timeout=60_000) as dl:
                        page.click("#dwpExcelBtn")
                    dl.value.save_as(output_path)
                    print(f"[download] Saved to {output_path}")

                except Exception as e:
                    try:
                        page.screenshot(path="radius_error.png")
                        print("[download] Screenshot saved to radius_error.png")
                    except Exception:
                        pass
                    raise RuntimeError(f"[download] Radius automation failed: {e}") from e

    return output_path
