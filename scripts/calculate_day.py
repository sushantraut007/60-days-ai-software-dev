"""Calculate which day number to deploy today."""

import os, sys, glob
from datetime import date, datetime
sys.path.insert(0, os.path.dirname(__file__))
from projects_registry import get_project

def out(key, val):
    f = os.environ.get("GITHUB_OUTPUT")
    if f:
        open(f, "a").write(f"{key}={val}\n")
    print(f"  {key}={val}")

def main():
    override = os.environ.get("DAY_OVERRIDE", "").strip()
    if override and override.isdigit():
        day = int(override)
    else:
        start_env = os.environ.get("PROJECT_START_DATE", "").strip()
        if start_env:
            try:
                start = datetime.strptime(start_env, "%Y-%m-%d").date()
                day = max(1, min((date.today() - start).days + 1, 60))
            except ValueError:
                day = 1
        else:
            existing = glob.glob("day-*/")
            day = len(existing) + 1

    project = get_project(day)
    if not project:
        print(f"Day {day} out of range or campaign complete.")
        sys.exit(0)

    print(f"Deploying Day {day}: {project['title']} [{project['phase']}]")
    out("day_number",    str(day))
    out("project_title", project["title"])
    out("project_phase", project["phase"])

if __name__ == "__main__":
    main()
