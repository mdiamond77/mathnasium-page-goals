"""
download.py
Logs into Radius and downloads the Digital Workout Plan Report
for the specified month. Returns the local file path.
"""

import os
from datetime import date
from dateutil.relativedelta import relativedelta
from playwright.sync_api import sync_playwright

from config import RADIUS_LOGIN_URL, RADIUS_DWP_URL, INPUT_DIR

RADIUS_USERNAME = os.environ["RADIUS_USERNAME"]
RADIUS_PASSWORD = os.environ["RADIUS_PASSWORD"]

# Center IDs: Englewood + Teaneck
CENTER_VALUES = ["2428", "2871"]


def download_dwp_report(data_month: date) -> str:
    """
    Download the Digital Workout Plan report for the given month.
    data_month: first day of the month to download.
    Returns the local path to the downloaded file.
    """
    os.makedirs(INPUT_DIR, exist_ok=True)
    output_path = os.path.join(
        INPUT_DIR,
        f"Digital_Workout_Plan_{data_month.strftime('%Y_%m')}.xlsx"
    )

    start = data_month.replace(day=1)
    # Last day of month
    end = (data_month + relativedelta(months=1)) - relativedelta(days=1)

    # Render JS array with double quotes (Python list uses single quotes, invalid JS)
    center_values_js = '["2428", "2871"]'

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        print(f"[download] Logging into Radius...")
        page.goto(RADIUS_LOGIN_URL)
        page.wait_for_load_state("networkidle")
        page.fill("#UserName", RADIUS_USERNAME)
        page.fill("#Password", RADIUS_PASSWORD)
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
        page.wait_for_timeout(4000)

        # Download Excel
        print("[download] Downloading report...")
        with page.expect_download() as dl:
            page.click("#dwpExcelBtn")
        dl.value.save_as(output_path)
        print(f"[download] Saved to {output_path}")

        browser.close()

    return output_path
