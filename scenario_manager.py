

import json
import os
from datetime import datetime

import google.generativeai as genai

# ── Renderer catalogue ────────────────────────────────────────────────────────
AVAILABLE_RENDERERS = {
    "traffic_light": (
        "Traffic light that cycles through states (red/yellow/green). "
        "Uses the 'states' list in animation config. No 'object' field needed."
    ),
    "linear_horizontal": (
        "Object moves in a straight horizontal line from one side to the other. "
        "Requires an 'object' field chosen from COMPATIBLE_OBJECTS."
    ),
    "wave_horizontal": (
        "Object moves horizontally while oscillating vertically (sine wave). "
        "Requires 'object': 'bird'."
    ),
    "door_animation": (
        "A door swings open from 0° to max_angle. No 'object' field needed."
    ),
    "particle_system": (
        "Many small particles (rain drops, snow) fall or drift across the frame. "
        "No 'object' field needed."
    ),
    "vertical_rise": (
        "Object rises vertically from bottom to top (or sets from top to bottom). "
        "Requires 'object': 'sun'."
    ),
}

# Objects compatible with each renderer that needs one
RENDERER_REQUIRED_OBJECTS = {
    "linear_horizontal": ["person", "car", "ball"],
    "wave_horizontal":   ["bird"],
    "vertical_rise":     ["sun"],
    # renderers below use built-in drawing – no 'object' field
    "traffic_light":   [],
    "door_animation":  [],
    "particle_system": [],
}

AVAILABLE_BACKGROUNDS = {
    "street":       "Road with lane markings and sky above",
    "indoor":       "Plain beige/warm interior wall",
    "grass":        "Green grass ground with light-blue sky above",
    "sky":          "Solid light-blue sky",
    "cloudy":       "Flat grey overcast sky",
    "gradient_sky": "Warm gradient sky (dawn / dusk feel)",
}

AVAILABLE_OBJECTS = {
    "person": "Stick-figure person (head, body, arms, legs)",
    "car":    "Simple car with body, roof, windows and wheels",
    "ball":   "Filled circle with a specular highlight",
    "bird":   "Small bird with ellipse body and animated flapping wings",
    "sun":    "Bright circle with radiating line-rays",
}

# ── Gemini model ──────────────────────────────────────────────────────────────
# Using gemini-2.0-flash which is available on Google AI Studio (v1beta API).
# The older alias "gemini-1.5-flash-latest" was removed from v1beta and will
# return a 404 – use an explicit stable model name instead.
GEMINI_MODEL_NAME = "gemini-2.0-flash"

# ─────────────────────────────────────────────────────────────────────────────


class ScenarioManager:
    """
    Manages the lifecycle of CAPTCHA scenario definitions stored in scenarios.json.

    On startup it loads the file, and – if a Gemini API key is supplied –
    can auto-expand the scenario pool to a desired target count.
    """

    def __init__(self, scenarios_file: str = "scenarios.json", gemini_api_key: str = None):
        self.scenarios_file    = scenarios_file
        self.gemini_api_key    = gemini_api_key
        self.gemini_model      = None
        self.gemini_configured = False

        self._configure_gemini()
        self._data = self._load_file()

    # ── Gemini setup ──────────────────────────────────────────────────────────

    def _configure_gemini(self):
        key = self.gemini_api_key or ""
        if key and key not in ("your-gemini-api-key-here", "") and len(key) > 20:
            try:
                # Do NOT pass transport="rest" – let the SDK choose automatically.
                genai.configure(api_key=key)
                self.gemini_model      = genai.GenerativeModel(GEMINI_MODEL_NAME)
                self.gemini_configured = True
                print(f"✅ Gemini configured for automatic scenario generation "
                      f"(model: {GEMINI_MODEL_NAME})")
            except Exception as exc:
                print(f"❌ Gemini configuration failed: {exc}")
        else:
            print("⚠️  Gemini API key not set – automatic scenario generation disabled")

    # ── File I/O ──────────────────────────────────────────────────────────────

    def _load_file(self) -> dict:
        if os.path.exists(self.scenarios_file):
            with open(self.scenarios_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            count = len(data.get("scenarios", []))
            print(f"✅ Loaded {count} scenarios from {self.scenarios_file}")
            return data
        print(f"⚠️  {self.scenarios_file} not found – starting with empty scenario list")
        return {"version": "1.0", "last_updated": datetime.now().isoformat(), "scenarios": []}

    def _save_file(self):
        self._data["last_updated"] = datetime.now().isoformat()
        with open(self.scenarios_file, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)
        total = len(self._data.get("scenarios", []))
        print(f"✅ Saved {total} scenarios → {self.scenarios_file}")

    def reload(self):
        """Reload scenarios from disk (useful after external edits)."""
        self._data = self._load_file()

    # ── Public accessors ──────────────────────────────────────────────────────

    def get_scenarios(self) -> list:
        return self._data.get("scenarios", [])

    def get_scenario_ids(self) -> list:
        return [s["id"] for s in self.get_scenarios()]

    def scenario_count(self) -> int:
        return len(self.get_scenarios())

    # ── Adding scenarios ──────────────────────────────────────────────────────

    def add_scenario(self, scenario_def: dict) -> bool:
        """Validate and append *scenario_def* to the JSON file. Returns True on success."""
        if scenario_def["id"] in self.get_scenario_ids():
            print(f"⚠️  Scenario '{scenario_def['id']}' already exists – skipping")
            return False

        if not self._validate(scenario_def):
            return False

        self._data.setdefault("scenarios", []).append(scenario_def)
        self._save_file()
        print(f"✅ Added new scenario: {scenario_def['id']} – \"{scenario_def.get('name', '')}\"")
        return True

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate(self, s: dict) -> bool:
        """Return True only if *s* is a structurally valid scenario definition."""
        for field in ("id", "name", "renderer", "background", "questions"):
            if field not in s:
                print(f"❌ Validation failed: missing field '{field}'")
                return False

        if s["renderer"] not in AVAILABLE_RENDERERS:
            print(f"❌ Unknown renderer '{s['renderer']}'. Valid: {list(AVAILABLE_RENDERERS)}")
            return False

        if s["background"] not in AVAILABLE_BACKGROUNDS:
            print(f"❌ Unknown background '{s['background']}'. Valid: {list(AVAILABLE_BACKGROUNDS)}")
            return False

        required_objects = RENDERER_REQUIRED_OBJECTS.get(s["renderer"], [])
        if required_objects:
            obj = s.get("object", "")
            if obj not in required_objects:
                print(f"❌ Renderer '{s['renderer']}' needs object in "
                      f"{required_objects}, got '{obj}'")
                return False

        if not s.get("questions"):
            print("❌ No questions defined")
            return False

        for idx, q in enumerate(s["questions"]):
            if "template" not in q:
                print(f"❌ Question {idx} missing 'template'")
                return False
            has_answer = any(k in q for k in ("answer", "answer_key", "answer_map"))
            if not has_answer:
                print(f"❌ Question {idx} has no answer definition")
                return False

        return True

    # ── Gemini generation ─────────────────────────────────────────────────────

    def generate_with_gemini(self) -> dict | None:
        """Ask Gemini to produce one new scenario definition. Returns the dict or None."""
        if not self.gemini_configured:
            print("❌ Gemini not configured – cannot generate new scenarios")
            return None

        existing_summary = json.dumps(
            [{"id": s["id"], "renderer": s.get("renderer", ""), "name": s.get("name", "")}
             for s in self.get_scenarios()],
            indent=2
        )

        prompt = f"""You are designing new video CAPTCHA scenarios for a security system.

AVAILABLE RENDERERS (choose exactly one):
{json.dumps(AVAILABLE_RENDERERS, indent=2)}

AVAILABLE BACKGROUNDS (choose exactly one):
{json.dumps(AVAILABLE_BACKGROUNDS, indent=2)}

OBJECT COMPATIBILITY:
- linear_horizontal  → object must be one of: {RENDERER_REQUIRED_OBJECTS['linear_horizontal']}
- wave_horizontal    → object must be: "bird"
- vertical_rise      → object must be: "sun"
- traffic_light, door_animation, particle_system → NO "object" field

AVAILABLE OBJECTS (for renderers that need one):
{json.dumps(AVAILABLE_OBJECTS, indent=2)}

EXISTING SCENARIOS (do NOT duplicate these IDs or concepts):
{existing_summary}

TASK: Generate exactly ONE new scenario as a JSON object.

RULES:
1. id must be snake_case and not in: {self.get_scenario_ids()}
2. Questions must be answerable by watching the short video clip
3. Answers must be short common words: yes/no/left/right/morning/evening/rainy/sunny/more/less etc.
4. Include 3-5 questions per scenario
5. For linear_horizontal/wave_horizontal/vertical_rise you MUST include "object"
6. Use {{direction}} as a placeholder in the template when the answer depends on the random direction chosen at runtime, paired with "answer_key": "direction"
7. Use {{next_state}} as a placeholder when the answer depends on the traffic-light state, paired with "answer_map" + "answer_map_key": "next_state"
8. Use "answer": "fixed_word" for questions with a constant answer

RETURN ONLY VALID JSON (no markdown fences, no explanation):
{{
  "id": "unique_snake_case_id",
  "name": "Human Readable Name",
  "description": "One sentence describing what is visible in the video",
  "renderer": "chosen_renderer",
  "background": "chosen_background",
  "object": "compatible_object_if_needed",
  "object_config": {{
    "y_ratio": 0.6
  }},
  "animation": {{
    "type": "chosen_renderer",
    "direction": "random"
  }},
  "questions": [
    {{"template": "Question using {{direction}}?", "answer_key": "direction"}},
    {{"template": "Fixed-answer question?", "answer": "yes"}}
  ]
}}"""

        try:
            print(f"🤖 Asking Gemini ({GEMINI_MODEL_NAME}) to generate a new scenario…")
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature":      0.7,
                    "max_output_tokens": 2048,
                }
            )
            response_text = response.text.strip()

            # Strip markdown fences if present
            if "```json" in response_text:
                start         = response_text.find("```json") + 7
                end           = response_text.rfind("```")
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start         = response_text.find("```") + 3
                end           = response_text.rfind("```")
                response_text = response_text[start:end].strip()

            scenario_def = json.loads(response_text)

            if self._validate(scenario_def):
                print(f"✅ Gemini produced valid scenario: '{scenario_def['id']}'")
                return scenario_def
            else:
                print("❌ Gemini scenario failed validation")
                return None

        except json.JSONDecodeError as exc:
            print(f"❌ Could not parse Gemini response as JSON: {exc}")
            return None
        except Exception as exc:
            print(f"❌ Gemini generation error: {exc}")
            return None

    # ── Auto-expansion ────────────────────────────────────────────────────────

    def auto_expand(self, target_count: int = 12) -> int:
        """
        Expand the scenario pool to *target_count* by generating new ones with Gemini.
        Returns the final number of scenarios.
        """
        current = self.scenario_count()

        if current >= target_count:
            print(f"✅ Already have {current} scenarios (target={target_count}) – "
                  f"no expansion needed")
            return current

        if not self.gemini_configured:
            print(f"⚠️  Gemini not configured – keeping {current} scenario(s)")
            return current

        needed       = target_count - current
        max_attempts = needed * 3
        added        = 0

        print(f"🚀 Expanding scenarios: {current} → {target_count} (need {needed} more)")

        for attempt in range(max_attempts):
            if added >= needed:
                break
            print(f"\n🔄 Attempt {attempt + 1}/{max_attempts} "
                  f"(need {needed - added} more scenario(s))")
            new_scenario = self.generate_with_gemini()
            if new_scenario and self.add_scenario(new_scenario):
                added += 1

        final = self.scenario_count()
        print(f"\n🎉 Auto-expansion complete! Total scenarios: {final}")
        return final