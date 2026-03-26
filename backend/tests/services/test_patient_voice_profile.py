import sys
import types
from types import SimpleNamespace

google_module = sys.modules.setdefault("google", types.ModuleType("google"))
genai_module = types.ModuleType("google.genai")
genai_module.Client = object
genai_types_module = types.ModuleType("google.genai.types")
genai_types_module.GenerateContentConfig = object
genai_module.types = genai_types_module
google_module.genai = genai_module
sys.modules["google.genai"] = genai_module
sys.modules["google.genai.types"] = genai_types_module

from services.patient_voice_profile import infer_patient_voice_profile


def test_infer_patient_voice_profile_for_older_male_case():
    case = SimpleNamespace(
        title="Lung cancer follow-up",
        patient_background="A 78-year-old man who is retired and anxious about his prognosis.",
        script="He asks if the treatment is still working.",
    )

    profile = infer_patient_voice_profile(case, base_instructions="Speak naturally.")

    assert profile.age_group == "older_adult"
    assert profile.gender == "male"
    assert profile.voice_id == "sage"
    assert "older man" in profile.instructions
    assert "worried delivery" in profile.instructions


def test_infer_patient_voice_profile_for_child_case():
    case = SimpleNamespace(
        title="Pediatric asthma check-in",
        patient_background="An 8-year-old girl brought in by her mother.",
        script="She is nervous and speaks in short sentences.",
    )

    profile = infer_patient_voice_profile(case, base_instructions="Speak naturally.")

    assert profile.age_group == "child"
    assert profile.gender == "female"
    assert profile.voice_id == "shimmer"
    assert "young girl" in profile.instructions


def test_infer_patient_voice_profile_adds_style_without_demographic_voice_change():
    case = SimpleNamespace(
        title="Acute dyspnea",
        patient_background="The patient is short of breath, tired, and in pain.",
        script="Answer in brief phrases because speaking is difficult.",
    )

    profile = infer_patient_voice_profile(case, base_instructions="Speak naturally.")

    assert profile.voice_id == "default"
    assert profile.age_group is None
    assert profile.gender is None
    assert "shorter phrases" in profile.instructions
    assert "fatigued" in profile.instructions
    assert "discomfort" in profile.instructions


def test_infer_patient_voice_profile_falls_back_when_case_is_ambiguous():
    case = SimpleNamespace(
        title="General follow-up",
        patient_background="The patient returns for a routine check-in.",
        script="No clear demographic or emotional markers are provided.",
    )

    profile = infer_patient_voice_profile(case, base_instructions="Speak naturally.")

    assert profile.voice_id == "default"
    assert profile.age_group is None
    assert profile.gender is None
    assert profile.style_tags == ()
    assert profile.instructions == "Speak naturally."
