"""Infer a best-effort TTS voice profile from case text."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


_AGE_PATTERN = re.compile(r"\b(\d{1,3})\s*[- ]?(?:year|yr)s?[- ]?old\b", re.IGNORECASE)

_CHILD_CUES = (
    "child",
    "pediatric",
    "paediatric",
    "kid",
    "toddler",
    "preschool",
    "infant",
    "baby",
    "school-aged",
    "school age",
)
_TEEN_CUES = (
    "teen",
    "teenage",
    "adolescent",
    "high school",
)
_YOUNG_ADULT_CUES = (
    "young adult",
    "college student",
    "in her 20s",
    "in his 20s",
    "in their 20s",
    "in her twenties",
    "in his twenties",
    "in their twenties",
)
_OLDER_ADULT_CUES = (
    "elderly",
    "older adult",
    "senior",
    "geriatric",
    "retired",
    "frail",
    "grandmother",
    "grandfather",
)

_FEMALE_CUES = (
    "female",
    "woman",
    "girl",
    "lady",
    "mother",
    "mom",
    "wife",
    "grandmother",
    "pregnant",
)
_MALE_CUES = (
    "male",
    "man",
    "boy",
    "gentleman",
    "father",
    "dad",
    "husband",
    "grandfather",
)

_STYLE_CUES: dict[str, tuple[str, ...]] = {
    "anxious": ("anxious", "worried", "nervous", "fearful", "afraid", "panicked"),
    "calm": ("calm", "collected", "reassured", "stoic"),
    "frail": ("frail", "weak", "fragile"),
    "confused": ("confused", "uncertain", "forgetful", "disoriented"),
    "short_of_breath": ("short of breath", "breathless", "dyspnea", "dyspnoea", "winded"),
    "tired": ("tired", "fatigued", "exhausted", "drained"),
    "pain": ("pain", "painful", "hurting", "uncomfortable", "grimacing"),
}

_VOICE_BY_DEMOGRAPHIC: dict[tuple[str | None, str | None], str] = {
    ("child", "female"): "shimmer",
    ("child", "male"): "echo",
    ("child", None): "nova",
    ("teen", "female"): "nova",
    ("teen", "male"): "alloy",
    ("teen", None): "nova",
    ("young_adult", "female"): "coral",
    ("young_adult", "male"): "cedar",
    ("young_adult", None): "marin",
    ("adult", "female"): "coral",
    ("adult", "male"): "cedar",
    ("older_adult", "female"): "ballad",
    ("older_adult", "male"): "sage",
    ("older_adult", None): "sage",
}


@dataclass(frozen=True, slots=True)
class PatientVoiceProfile:
    """Resolved TTS hints for a patient turn."""

    voice_id: str = "default"
    instructions: str | None = None
    age_group: str | None = None
    gender: str | None = None
    style_tags: tuple[str, ...] = ()


def infer_patient_voice_profile(case: Any, base_instructions: str | None = None) -> PatientVoiceProfile:
    """Infer a best-effort voice profile from case metadata."""
    text = _build_case_text(case)
    age_group = _detect_age_group(text)
    gender = _detect_gender(text)
    style_tags = _detect_style_tags(text)

    voice_id = _VOICE_BY_DEMOGRAPHIC.get((age_group, gender), "default")
    instructions = _build_instructions(base_instructions, age_group, gender, style_tags)

    return PatientVoiceProfile(
        voice_id=voice_id,
        instructions=instructions,
        age_group=age_group,
        gender=gender,
        style_tags=style_tags,
    )


def _build_case_text(case: Any) -> str:
    parts = (
        getattr(case, "title", None),
        getattr(case, "patient_background", None),
        getattr(case, "script", None),
    )
    return " ".join(part.strip().lower() for part in parts if isinstance(part, str) and part.strip())


def _detect_age_group(text: str) -> str | None:
    if not text:
        return None

    age_match = _AGE_PATTERN.search(text)
    if age_match:
        age = int(age_match.group(1))
        if age <= 12:
            return "child"
        if age <= 17:
            return "teen"
        if age <= 35:
            return "young_adult"
        if age >= 65:
            return "older_adult"
        return "adult"

    if _contains_any(text, _CHILD_CUES):
        return "child"
    if _contains_any(text, _TEEN_CUES):
        return "teen"
    if _contains_any(text, _YOUNG_ADULT_CUES):
        return "young_adult"
    if _contains_any(text, _OLDER_ADULT_CUES):
        return "older_adult"
    return None


def _detect_gender(text: str) -> str | None:
    if not text:
        return None

    female_matches = _count_matches(text, _FEMALE_CUES)
    male_matches = _count_matches(text, _MALE_CUES)

    if female_matches and male_matches:
        return None
    if female_matches:
        return "female"
    if male_matches:
        return "male"
    return None


def _detect_style_tags(text: str) -> tuple[str, ...]:
    if not text:
        return ()

    matched_tags = [tag for tag, cues in _STYLE_CUES.items() if _contains_any(text, cues)]
    return tuple(matched_tags)


def _build_instructions(
    base_instructions: str | None,
    age_group: str | None,
    gender: str | None,
    style_tags: tuple[str, ...],
) -> str | None:
    detail_segments: list[str] = []

    demographic_phrase = _describe_demographic(age_group, gender)
    if demographic_phrase:
        detail_segments.append(f"The patient should sound like {demographic_phrase}.")

    for tag in style_tags:
        detail_segments.append(_instruction_for_style(tag))

    if not base_instructions and not detail_segments:
        return None
    if not detail_segments:
        return base_instructions
    if not base_instructions:
        return " ".join(detail_segments)
    return f"{base_instructions.strip()} {' '.join(detail_segments)}"


def _describe_demographic(age_group: str | None, gender: str | None) -> str | None:
    if age_group == "child":
        if gender == "female":
            return "a young girl"
        if gender == "male":
            return "a young boy"
        return "a child"
    if age_group == "teen":
        if gender == "female":
            return "a teenage girl"
        if gender == "male":
            return "a teenage boy"
        return "a teenager"
    if age_group == "young_adult":
        if gender == "female":
            return "a young adult woman"
        if gender == "male":
            return "a young adult man"
        return "a young adult"
    if age_group == "adult":
        if gender == "female":
            return "an adult woman"
        if gender == "male":
            return "an adult man"
        return "an adult"
    if age_group == "older_adult":
        if gender == "female":
            return "an older woman"
        if gender == "male":
            return "an older man"
        return "an older adult"
    if gender == "female":
        return "a woman"
    if gender == "male":
        return "a man"
    return None


def _instruction_for_style(tag: str) -> str:
    style_instructions = {
        "anxious": "Use a slightly tense, worried delivery with occasional hesitation.",
        "calm": "Keep the delivery steady, grounded, and measured.",
        "frail": "Use a softer, more delicate delivery that suggests low physical energy.",
        "confused": "Sound mildly uncertain and tentative without becoming incoherent.",
        "short_of_breath": "Use shorter phrases and light breathiness while keeping speech clear.",
        "tired": "Sound somewhat fatigued with gentler pacing and lower energy.",
        "pain": "Let discomfort come through subtly in the tone while staying intelligible.",
    }
    return style_instructions[tag]


def _contains_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def _count_matches(text: str, cues: tuple[str, ...]) -> int:
    return sum(1 for cue in cues if cue in text)
