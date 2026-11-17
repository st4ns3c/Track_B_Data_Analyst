"""
Nutrition programme: run the report every Monday at 07:00
---------------------------------------------------------
Build plan
  Problem : the director should find a fresh report every Monday morning
            without anyone remembering to run it.
  Input   : weekly_report.build_report().
  Output  : a new reports/report_YYYY-MM-DD.html each Monday at 07:00, and
            a line in logs/report.log for every run, including failures.

This keeps a Python process running and wakes it once a minute to check
the schedule. It uses the computer's local time, so on a machine set to
East Africa Time the report runs at 07:00 Nairobi time. If the machine is
off or asleep at 07:00 on Monday, that week's run is missed; the README
shows the cron line to use on a server that is always on.

Usage:
    python schedule_reports.py            # wait and run every Monday at 07:00
    python schedule_reports.py --run-now  # build one report now, then exit

Requirements:
    pip install schedule pandas numpy matplotlib
"""

import argparse
import logging
import time

import schedule

import weekly_report


def weekly_job():
    # Any failure is logged and the loop keeps going, so one bad week does
    # not stop next Monday's report.
    try:
        out = weekly_report.build_report()
        logging.info(f"Scheduled run finished: {out.name}")
    except weekly_report.ReportError as problem:
        logging.error(f"Scheduled run failed: {problem}")
    except Exception as error:
        logging.exception(f"Scheduled run failed unexpectedly: {error}")


def main():
    parser = argparse.ArgumentParser(description="Run the nutrition report every Monday at 07:00.")
    parser.add_argument("--run-now", action="store_true", help="build one report now and exit")
    args = parser.parse_args()

    weekly_report.setup_logging()
    if args.run_now:
        weekly_job()
        return

    schedule.every().monday.at("07:00").do(weekly_job)
    logging.info(f"Scheduler started. Next report: {schedule.next_run():%A %d %B %Y at %H:%M}")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
