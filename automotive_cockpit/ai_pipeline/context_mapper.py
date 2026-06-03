"""
context_mapper.py
-----------------
Pre-processor that maps natural/colloquial phrases to structured intents
BEFORE the SLM is invoked. Returns None if no pattern matches so the SLM
can handle it instead.

Resolution order (first match wins):
  1. Percentage extraction  — "open sunroof to 70%" → open_sunroof(70)
  2. Specific contextual idioms — "I'm feeling hot" → decrease_temperature(2)
  3. Generic open/close with defaults
"""

import re
from typing import Optional

# ── Helpers ───────────────────────────────────────────────────────────────────

# Words that mean percentage positions
_PERCENT_WORDS = {
    "quarter":  25,
    "half":     50,
    "halfway":  50,
    "three quarter": 75,
    "three-quarter": 75,
    "full":     100,
    "fully":    100,
    "complete": 100,
    "all the way": 100,
    "maximum":  100,
    "max":      100,
    "minimum":  0,
    "min":      0,
    "little":   25,
    "slightly": 20,
    "bit":      20,
    "a bit":    20,
}


def _extract_percent(text: str) -> Optional[int]:
    """
    Try to extract a percentage value from text.
    Handles:
      - Explicit digits: "70%", "to 70", "at 50 percent"
      - Word fractions: "halfway", "quarter", "full", "a little"
    Returns int (0-100) or None if nothing found.
    """
    # Try digit-based percentage: "to 70%", "70 percent", "at 70"
    m = re.search(r"\b(\d{1,3})\s*(?:%|percent)\b", text)
    if m:
        return max(0, min(100, int(m.group(1))))

    # Try "to/at/by <number>" without percent sign
    m = re.search(r"\b(?:to|at)\s+(\d{1,3})\b", text)
    if m:
        return max(0, min(100, int(m.group(1))))

    # Try word fractions (longest match first)
    for word, val in sorted(_PERCENT_WORDS.items(), key=lambda x: -len(x[0])):
        if re.search(r"\b" + re.escape(word) + r"\b", text):
            return val

    return None


# ── Fixed-value contextual phrase map ────────────────────────────────────────
# Order matters — more specific patterns must come before generic ones.
# Format: ([regex patterns], function_name, default_value)

CONTEXTUAL_MAP = [
    # ── Feeling hot / warm / stuffy ───────────────────────────────────────
    (["feel.*hot", r"\btoo hot\b", r"\bit.*hot\b", r"\bso hot\b", "burning",
      r"\bsweat(ing)?\b", "warm in here", "too warm", "boiling",
      "roasting", "stuffy", "suffocating"],
     "decrease_temperature", 2),

    # ── Feeling cold / chilly ─────────────────────────────────────────────
    (["feel.*cold", "too cold", r"\bit.*cold\b", "freezing", "chilly",
      "shivering", "chill in here", "bit cold", "very cold"],
     "increase_temperature", 2),

    # ── It's raining / windy → close sunroof (must come before open patterns)
    (["starting to rain", "it.*raining", "raining outside", "going to rain",
      "too windy", "wind.*loud", "getting wet"],
     "close_sunroof", 0),

    # ── Fresh air / ventilation (generic — no window position specified) ──
    (["fresh air", "need.*air", "want.*air",
      "let.*air in", "some air", "let.*breathe", r"\bcan.*breathe\b",
      "hard to breathe", "need ventilation"],
     "open_sunroof", 50),

    # ── Close sunroof ─────────────────────────────────────────────────────
    ([r"\bclose.*sunroof\b", r"\bshut.*sunroof\b",
      r"\bclose.*roof\b",   r"\bshut.*roof\b",
      "roof.*completely closed", "roof.*shut"],
     "close_sunroof", 0),

    # ── Close window ─────────────────────────────────────────────────────
    ([r"\bclose.*window\b", r"\bshut.*window\b",
      "window.*closed", "window.*shut"],
     "close_window", 0),

    # ── Dark outside / need lights ────────────────────────────────────────
    (["getting dark", r"\bit.*dark\b", r"\bcan.?t see\b", "dark outside",
      "need.*light", "turn on.*light", "switch on.*light",
      "visibility.*low", "too dark"],
     "turn_on_headlights", 1),

    # ── Lights off ───────────────────────────────────────────────────────
    (["too bright", r"\blight.*off\b", "turn off.*light", "switch off.*light",
      "lights.*blinding", r"\bdon.?t need.*light\b"],
     "turn_off_headlights", 0),

    # ── AC on/off ────────────────────────────────────────────────────────
    (["turn on.*ac", "switch on.*ac", "start.*ac",
      r"\bac.*on\b", "start.*cooling"],
     "turn_on_ac", 1),

    (["turn off.*ac", "switch off.*ac", "stop.*ac",
      r"\bac.*off\b", "stop.*cooling"],
     "turn_off_ac", 0),

    # ── Fan adjustments ───────────────────────────────────────────────────
    (["fan.*low", "reduce.*fan", "lower.*fan", "slow.*fan",
      "fan.*quiet", "fan.*too loud", "fan.*minimum"],
     "set_fan_speed", 1),

    (["fan.*high", "fan.*full", "max.*fan", "increase.*fan",
      "boost.*fan", "fan.*speed up", "fan.*maximum"],
     "set_fan_speed", 6),

    (["fan.*medium", r"\bfan.*mid\b", "fan.*half", "moderate.*fan"],
     "set_fan_speed", 3),
]


def match_contextual_phrase(text: str) -> Optional[dict]:
    """
    Two-pass intent resolver:

    Pass 1 — Percentage extraction for sunroof/window commands:
      Catches "open sunroof to 70%", "open sunroof halfway", "open sunroof" etc.
      with explicit percentage or sensible defaults (open=50, close=0).

    Pass 2 — Contextual idiom matching:
      "I'm feeling hot", "It's getting dark", "I want fresh air", etc.

    Returns a structured intent dict, or None to let the SLM handle it.
    """
    text_lower = text.lower().strip()

    # ── Pass 1: Sunroof percentage commands ──────────────────────────────
    if re.search(r"\bsunroof\b|\broof\b", text_lower):
        pct = _extract_percent(text_lower)

        if re.search(r"\bopen\b|\bopen(ing)?\b", text_lower):
            # "open sunroof" → default 50%; "open sunroof to 70%" → 70%
            val = pct if pct is not None else 50
            _log("sunroof open", val)
            return {"function": "open_sunroof", "value": val}

        if re.search(r"\bclose\b|\bshut\b", text_lower):
            _log("sunroof close", 0)
            return {"function": "close_sunroof", "value": 0}

        if re.search(r"\bset\b|\badjust\b|\bmove\b|\bput\b", text_lower) and pct is not None:
            _log("sunroof set", pct)
            return {"function": "open_sunroof", "value": pct}

    # ── Pass 1: Window percentage commands ───────────────────────────────
    if re.search(r"\bwindow\b|\bwindows\b", text_lower):
        pct = _extract_percent(text_lower)

        if re.search(r"\bopen\b|\bopen(ing)?\b", text_lower):
            val = pct if pct is not None else 50
            _log("window open", val)
            return {"function": "open_window", "value": val}

        if re.search(r"\bclose\b|\bshut\b", text_lower):
            _log("window close", 0)
            return {"function": "close_window", "value": 0}

        if re.search(r"\bset\b|\badjust\b|\bmove\b|\bput\b", text_lower) and pct is not None:
            _log("window set", pct)
            return {"function": "open_window", "value": pct}

    # ── Pass 2: Fixed contextual idiom map ───────────────────────────────
    for patterns, function_name, value in CONTEXTUAL_MAP:
        for pattern in patterns:
            if re.search(pattern, text_lower):
                _log(f"pattern '{pattern}'", value, function_name)
                return {"function": function_name, "value": value}

    return None  # No match — fall through to SLM


def _log(label: str, value, func: str = ""):
    suffix = f" → {func}({value})" if func else f" → ({value})"
    print(f"[ContextMapper] Matched {label}{suffix}")
