import os
import requests
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv
from prompts import SCHEMA_PROMPT, VALIDATION_PROMPT, RECOVERY_PROMPT, LEARNING_PROMPT

load_dotenv()

OPENAI_KEY   = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_MODEL = (os.getenv("OPENAI_MODEL", "gpt-3.5-turbo") or "").strip()
OPENAI_URL   = "https://api.openai.com/v1/chat/completions"

if not OPENAI_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in your .env file")

HEADERS = {
    "Authorization": f"Bearer {OPENAI_KEY}",
    "Content-Type": "application/json"
}


def log_section(title: str, data: Any = None):
    """Helper to print formatted log sections."""
    print(f"\n{'='*60}")
    print(f"🧩 {title}")
    if data is not None:
        try:
            print(json.dumps(data, indent=2))
        except Exception:
            print(str(data))
    print(f"{'='*60}\n")


def call_openai(prompt: str, temperature: float = 0.0, max_tokens: int = 800) -> str:
    log_section("🔗 Calling OpenAI API", {"model": OPENAI_MODEL, "temperature": temperature})
    print("📝 Prompt snippet:\n", prompt[:500], "...\n")

    payload = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    resp = requests.post(OPENAI_URL, headers=HEADERS, json=payload)
    if resp.status_code != 200:
        print(f"❌ OpenAI API failed: {resp.status_code}")
        print(resp.text)
        raise RuntimeError(f"OpenAI API failed: {resp.status_code} - {resp.text}")

    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    print("✅ API Response snippet:\n", content, "...\n")
    return content


def schema_agent_impl(user_text: str) -> Dict[str, Any]:
    log_section("🏗️ Schema Agent Invoked", {"user_text": user_text})
    out = call_openai(SCHEMA_PROMPT.format(user_text=user_text), temperature=0.0)
    try:
        parsed = json.loads(out)
    except Exception:
        m = re.search(r"(\{[\s\S]*\})", out)
        parsed = json.loads(m.group(1)) if m else {}
    log_section("📘 Schema Agent Output", parsed)
    return parsed


def validation_agent_impl(schema: Dict[str, Any], submission: Dict[str, Any]) -> Dict[str, Any]:
    log_section("🧪 Validation Agent Invoked", {"schema": schema, "submission": submission})
    errors = {}

    for f in schema.get("fields", []):
        name = f.get("name")
        val = submission.get(name)
        if f.get("required") and (val in (None, "", [])):
            errors[name] = "This field is required."
            continue
        t = f.get("type")
        if val not in (None, "", []) and t == "email":
            if "@" not in str(val) or "." not in str(val):
                errors[name] = "Invalid email format."
        if val not in (None, "", []) and t == "number":
            try:
                num = float(val)
                cons = f.get("constraints") or {}
                if "min" in cons and num < cons["min"]:
                    errors[name] = f"Must be >= {cons['min']}"
                if "max" in cons and num > cons["max"]:
                    errors[name] = f"Must be <= {cons['max']}"
            except:
                errors[name] = "Must be a number."

    needs_llm = any("date" in (f.get("type") or "") for f in schema.get("fields", []))
    llm_result = {}
    if needs_llm:
        print("🧠 Detected date fields — invoking LLM-based validation...")
        prompt = VALIDATION_PROMPT.format(schema=json.dumps(schema, indent=2), submission=json.dumps(submission, indent=2))
        try:
            llm_out = call_openai(prompt, temperature=0.0)
            llm_result = json.loads(re.search(r"(\{[\s\S]*\})", llm_out).group(1))
            errors.update(llm_result.get("errors", {}))
        except Exception as e:
            print("⚠️ LLM Validation failed:", e)

    result = {"valid": len(errors) == 0, "errors": errors}
    log_section("📗 Validation Agent Output", result)
    return result


def recovery_agent_impl(schema: Dict[str, Any], submission: Dict[str, Any], errors: Dict[str, str]) -> Dict[str, Any]:
    log_section("🩺 Recovery Agent Invoked", {"schema": schema, "submission": submission, "errors": errors})
    prompt = RECOVERY_PROMPT.format(schema=json.dumps(schema, indent=2),
                                   submission=json.dumps(submission, indent=2),
                                   errors=json.dumps(errors, indent=2))
    out = call_openai(prompt, temperature=0.2)
    try:
        parsed = json.loads(out)
    except:
        m = re.search(r"(\{[\s\S]*\})", out)
        parsed = json.loads(m.group(1)) if m else {"suggestions": {}}
    log_section("📙 Recovery Agent Output", parsed)
    return parsed


def learning_agent_impl(schema: Dict[str, Any], submissions: List[Dict[str, Any]]) -> Dict[str, Any]:
    log_section("🧠 Learning Agent Invoked", {"schema": schema, "submissions_count": len(submissions)})
    prompt = LEARNING_PROMPT.format(schema=json.dumps(schema, indent=2), submissions=json.dumps(submissions, indent=2))
    out = call_openai(prompt, temperature=0.0)
    try:
        parsed = json.loads(out)
    except:
        m = re.search(r"(\{[\s\S]*\})", out)
        parsed = json.loads(m.group(1)) if m else {"insights": {}}
    log_section("📒 Learning Agent Output", parsed)
    return parsed