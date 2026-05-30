"""
Generate a complete project using Google Gemini API — 100% free.
Uses gemini-2.0-flash-lite which has higher free tier limits.
"""

import os, sys, json, re, time
import urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(__file__))
from projects_registry import get_project

# gemini-2.0-flash-lite has higher RPM on free tier than flash
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"

PHASE_CONTEXT = {
    "beginner":     "Explain every concept from scratch. Extensive inline comments. Keep code simple.",
    "intermediate": "Show real production patterns. Discuss trade-offs. Assume Python knowledge.",
    "advanced":     "Production-grade code with performance, monitoring, and scaling notes.",
    "expert":       "Cutting-edge techniques. Reference research where relevant. System-design thinking.",
}

PROMPT_TEMPLATE = """You are an expert AI/ML engineer. Generate a complete educational project package.
Output ONLY valid JSON — no markdown fences, no text outside the JSON object.

Project details:
DAY: {day}/60
TITLE: {title}
PHASE: {phase} — {phase_context}
TAGS: {tags}
DESCRIPTION: {desc}

Return this exact JSON schema:
{{
  "readme": "full markdown README: Problem, Solution, Architecture, Setup, Usage, Key concepts",
  "main_code": "complete working Python code with inline comments",
  "test_code": "pytest unit tests",
  "requirements": "requirements.txt content",
  "env_example": ".env.example content",
  "concepts_summary": "2 sentence summary of AI concepts covered"
}}

Rules: real working code only, PEP8, secrets via env vars, no pseudocode."""


def call_gemini(prompt: str) -> str:
    api_key = os.environ["GEMINI_API_KEY"]
    url = f"{GEMINI_API_URL}?key={api_key}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 4096,   # reduced from 8192 to avoid rate limits
        }
    }).encode("utf-8")

    for attempt in range(6):
        # Wait before each attempt (except the first)
        if attempt > 0:
            wait = 60 * attempt   # 60s, 120s, 180s, 240s, 300s
            print(f"Waiting {wait}s before attempt {attempt + 1}/6...")
            time.sleep(wait)

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            # Check for blocked response
            if not data.get("candidates"):
                print(f"Empty candidates in response: {data}")
                continue

            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            print(f"HTTP {e.code} on attempt {attempt + 1}: {body[:300]}")
            if e.code not in (429, 500, 503):
                raise   # don't retry on 400, 401, 404 etc
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {e}")
            if attempt == 5:
                raise

    raise RuntimeError("Gemini API failed after 6 attempts")


def generate(day: int, title: str, phase: str) -> dict:
    project = get_project(day)

    prompt = PROMPT_TEMPLATE.format(
        day=day,
        title=title,
        phase=phase.upper(),
        phase_context=PHASE_CONTEXT.get(phase, ""),
        tags=", ".join(project["tags"]),
        desc=project["desc"],
    )

    print(f"Calling Gemini for Day {day}: {title}...")
    raw = call_gemini(prompt).strip()

    # Strip markdown fences if model adds them
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$",          "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw response preview: {raw[:500]}")
        raise


def write_files(day: int, title: str, phase: str, data: dict) -> str:
    slug   = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    folder = f"day-{day:02d}-{slug}"
    os.makedirs(folder, exist_ok=True)

    files = {
        "README.md":        data.get("readme", ""),
        "main.py":          data.get("main_code", ""),
        "test_main.py":     data.get("test_code", ""),
        "requirements.txt": data.get("requirements", ""),
        ".env.example":     data.get("env_example", ""),
    }

    for name, content in files.items():
        if content:
            with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  wrote {folder}/{name}")

    for extra in data.get("extra_files", []):
        if extra.get("filename") and extra.get("content"):
            with open(os.path.join(folder, extra["filename"]), "w", encoding="utf-8") as f:
                f.write(extra["content"])
            print(f"  wrote {folder}/{extra['filename']}")

    meta = {
        "day": day, "title": title, "phase": phase,
        "folder": folder, "concepts": data.get("concepts_summary", "")
    }
    with open(os.path.join(folder, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    return folder


def main():
    day   = int(os.environ["DAY_NUMBER"])
    title =     os.environ["PROJECT_TITLE"]
    phase =     os.environ["PROJECT_PHASE"]

    print(f"\n{'='*60}\nDay {day}: {title}\nPhase: {phase}\n{'='*60}\n")

    # Small initial delay to avoid hitting rate limits on cold start
    print("Waiting 10s before first API call...")
    time.sleep(10)

    data   = generate(day, title, phase)
    folder = write_files(day, title, phase, data)
    print(f"\nDone — {folder}/")


if __name__ == "__main__":
    main()
