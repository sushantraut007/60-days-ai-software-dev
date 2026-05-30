"""
Generate a complete project using GitHub Models — 100% free.
GitHub Models uses the OpenAI-compatible API endpoint with your GITHUB_TOKEN.
No extra API key needed — GITHUB_TOKEN is injected automatically in Actions.
"""

import os, sys, json, re
sys.path.insert(0, os.path.dirname(__file__))
from projects_registry import get_project
from openai import OpenAI

# GitHub Models endpoint — free with any GitHub account
GITHUB_MODELS_ENDPOINT = "https://models.inference.ai.azure.com"
# Best free model available on GitHub Models as of 2025
MODEL = "gpt-4o"

SYSTEM_PROMPT = """You are an expert AI/ML engineer creating a world-class educational
GitHub repository about AI in software development.

Generate a COMPLETE, production-quality project package. Output ONLY valid JSON — no
markdown fences, no preamble, nothing outside the JSON object.

Required JSON schema:
{
  "readme": "full markdown README — include: Problem, Solution, Architecture, Setup, Usage, Code walkthrough, Key concepts, Extensions",
  "main_code": "complete working Python code with comments explaining every AI/ML concept",
  "test_code": "pytest tests covering normal, edge, and error cases",
  "requirements": "requirements.txt content",
  "env_example": ".env.example with all required environment variables",
  "dockerfile": "Dockerfile (omit field if not applicable)",
  "extra_files": [{"filename": "utils.py", "content": "..."} ],
  "concepts_summary": "2-3 sentence summary of AI concepts covered"
}

Code requirements:
- Fully working (not pseudocode)
- Proper error handling and logging
- Secrets via environment variables only
- Well-commented, explaining AI/ML concepts inline
- PEP8 compliant"""

PHASE_CONTEXT = {
    "beginner":     "Explain every concept from scratch. Extensive inline comments. Keep code simple and readable.",
    "intermediate": "Show real production patterns. Discuss architecture trade-offs. Assume Python knowledge.",
    "advanced":     "Production-grade code with performance considerations, monitoring, and scaling notes.",
    "expert":       "Cutting-edge techniques. Reference relevant research. System-design thinking throughout.",
}

def generate(day: int, title: str, phase: str) -> dict:
    project = get_project(day)
    client  = OpenAI(
        base_url=GITHUB_MODELS_ENDPOINT,
        api_key=os.environ["GITHUB_TOKEN"],   # free — auto-injected by GitHub Actions
    )

    prompt = f"""Generate a complete project for:

DAY: {day}/60  
TITLE: {title}
PHASE: {phase.upper()} — {PHASE_CONTEXT.get(phase, '')}
TAGS: {', '.join(project['tags'])}
DESCRIPTION: {project['desc']}

Context: This is part of a 60-day AI in software development curriculum.
Days 1-14 = beginner basics | Days 15-35 = intermediate patterns |
Days 36-50 = advanced production | Days 51-60 = expert systems.

Make the README the best educational resource on this topic on the internet.
All code must actually run."""

    print(f"Calling GitHub Models ({MODEL}) for Day {day}: {title}...")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.3,
        max_tokens=8000,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if model adds them
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$",          "", raw)
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
            path = os.path.join(folder, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  wrote {path}")

    for extra in data.get("extra_files", []):
        if extra.get("filename") and extra.get("content"):
            path = os.path.join(folder, extra["filename"])
            with open(path, "w", encoding="utf-8") as f:
                f.write(extra["content"])
            print(f"  wrote {path}")

    # Metadata for tracker
    import json as _json
    meta = {"day": day, "title": title, "phase": phase,
            "folder": folder, "concepts": data.get("concepts_summary", "")}
    with open(os.path.join(folder, "meta.json"), "w") as f:
        _json.dump(meta, f, indent=2)

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
