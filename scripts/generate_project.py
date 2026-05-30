"""
Generate a complete project using Google Gemini API — 100% free.
Free tier: 1,500 requests/day, no credit card needed.
"""

import os, sys, json, re
import urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(__file__))
from projects_registry import get_project

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

SYSTEM_PROMPT = """You are an expert AI/ML engineer creating a world-class educational
GitHub repository about AI in software development.

Generate a COMPLETE, production-quality project package.
Output ONLY valid JSON — no markdown fences, no preamble, nothing outside the JSON.

Required JSON schema:
{
  "readme": "full markdown README with: Problem, Solution, Architecture, Setup, Usage, Code walkthrough, Key concepts, Extensions",
  "main_code": "complete working Python code with comments explaining every AI/ML concept",
  "test_code": "pytest tests covering normal, edge, and error cases",
  "requirements": "requirements.txt content",
  "env_example": ".env.example with all required environment variables",
  "dockerfile": "Dockerfile content or empty string if not needed",
  "extra_files": [{"filename": "utils.py", "content": "..."}],
  "concepts_summary": "2-3 sentence summary of AI concepts covered"
}

Code must be fully working, not pseudocode. PEP8 compliant. Secrets via env vars only."""

PHASE_CONTEXT = {
    "beginner":     "Explain every concept from scratch. Extensive inline comments. Keep code simple.",
    "intermediate": "Show real production patterns. Discuss trade-offs. Assume Python knowledge.",
    "advanced":     "Production-grade code with performance, monitoring, and scaling notes.",
    "expert":       "Cutting-edge techniques. Reference research where relevant. System-design thinking.",
}

def call_gemini(prompt: str) -> str:
    api_key = os.environ["GEMINI_API_KEY"]
    url = f"{GEMINI_API_URL}?key={api_key}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 8192,
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return data["candidates"][0]["content"]["parts"][0]["text"]

def generate(day: int, title: str, phase: str) -> dict:
    project = get_project(day)

    prompt = f"""{SYSTEM_PROMPT}

Generate a complete project for:

DAY: {day}/60
TITLE: {title}
PHASE: {phase.upper()} — {PHASE_CONTEXT.get(phase, '')}
TAGS: {', '.join(project['tags'])}
DESCRIPTION: {project['desc']}

Context: 60-day AI in software development curriculum.
Days 1-14 = beginner | Days 15-35 = intermediate | Days 36-50 = advanced | Days 51-60 = expert.

Make the README the best educational resource on this topic. All code must actually run."""

    print(f"Calling Gemini for Day {day}: {title}...")
    raw = call_gemini(prompt).strip()

    # Strip markdown fences if model adds them
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)

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
    if data.get("dockerfile"):
        files["Dockerfile"] = data["dockerfile"]

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

    meta = {"day": day, "title": title, "phase": phase,
            "folder": folder, "concepts": data.get("concepts_summary", "")}
    with open(os.path.join(folder, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    return folder

def main():
    day   = int(os.environ["DAY_NUMBER"])
    title =     os.environ["PROJECT_TITLE"]
    phase =     os.environ["PROJECT_PHASE"]

    print(f"\n{'='*60}\nDay {day}: {title}\nPhase: {phase}\n{'='*60}\n")
    data   = generate(day, title, phase)
    folder = write_files(day, title, phase, data)
    print(f"\nDone — {folder}/")

if __name__ == "__main__":
    main()
