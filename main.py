"""
main.py
Orchestrates: download → process → deliver → log.
Usage:
    python main.py [--month YYYY-MM] [--trigger auto|manual]
"""

import argparse
import os
import sys
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from config import SUCCESS_RECIPIENTS, ERROR_RECIPIENTS, OUTPUT_DIR
from download import download_dwp_report
from process import process_report
from deliver import send_email, upload_to_drive
import run_log

SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
GOOGLE_DRIVE_CREDENTIALS = os.environ.get("GOOGLE_DRIVE_CREDENTIALS", "")


def parse_goal_month(month_str: str | None) -> datetime:
    if month_str:
        return datetime.strptime(month_str, "%Y-%m")
    return datetime.now()  # default: current month


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", help="Goal month (YYYY-MM), defaults to current month")
    parser.add_argument("--trigger", default="manual", choices=["auto", "manual"])
    args = parser.parse_args()

    goal_month = parse_goal_month(args.month)
    month_name = goal_month.strftime("%B")   # e.g. "May"
    month_key = goal_month.strftime("%Y-%m") # e.g. "2026-05"

    # For reruns (--month specified), pull 90 days ending the last day of the previous month
    # For current runs, pull 90 days ending today
    if args.month:
        as_of_date = (goal_month.replace(day=1) - relativedelta(days=1)).date()
    else:
        as_of_date = date.today()

    output_filename = f"{month_name} Page Goals.xlsx"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    print(f"[main] Processing {month_name} page goals (90 days ending {as_of_date})")

    try:
        # 1. Download
        input_path = download_dwp_report(as_of_date)

        # 2. Process
        process_report(input_path, output_path)
        print(f"[main] Report written to {output_path}")

        # 3. Upload to Drive
        drive_link = ""
        if GOOGLE_DRIVE_CREDENTIALS:
            try:
                drive_link = upload_to_drive(output_path, GOOGLE_DRIVE_CREDENTIALS)
            except Exception as e:
                print(f"[main] Drive upload failed (continuing): {e}")

        # 4. Email success
        send_email(output_path, month_name, SUCCESS_RECIPIENTS, SMTP_USER, SMTP_PASSWORD)

        # 5. Log success
        run_log.append_run(
            trigger=args.trigger,
            month=month_key,
            status="success",
            output_file=output_filename,
            drive_link=drive_link or None,
        )
        print(f"[main] ✅ Done. {month_name} page goals complete.")

    except Exception as e:
        error_msg = str(e)
        print(f"[main] ❌ Error: {error_msg}", file=sys.stderr)

        # Email error to Matt only
        try:
            send_email(None, month_name, ERROR_RECIPIENTS, SMTP_USER, SMTP_PASSWORD, error_message=error_msg)
        except Exception as email_err:
            print(f"[main] Failed to send error email: {email_err}", file=sys.stderr)

        # Log failure
        run_log.append_run(
            trigger=args.trigger,
            month=month_key,
            status="error",
            error=error_msg,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
