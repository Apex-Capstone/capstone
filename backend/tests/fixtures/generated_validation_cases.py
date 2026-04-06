"""
Seeded transcripts for evaluator validation: difficult diagnosis scenario.

Speaker mapping matches conversation_fixture.py:
- role \"user\" = clinician / trainee
- role \"assistant\" = simulated patient

Case concept: 52-year-old discussing concerning test results (likely cancer pending confirmation); patient anxious.

Clinician turns include ``expected_spikes`` so rule SPIKES coverage varies by variant. Assistant turns may
include minimal ``spans_json`` (empathy opportunities) and clinician turns ``metrics_json`` / response
spans so empathy linkage differentiates strong vs weak without duplicating the full GOOD/BAD fixtures.
"""

# --- Shared NLU-shaped snippets (compact, matches conversation_fixture style) ---

_U_MET = {
    "empathy": {"empathy_score": 0.0, "found_keywords": [], "has_empathy": False},
    "question_type": "closed",
    "tone": {"calm": True, "clear": True},
    "empathy_response": False,
    "empathy_response_type": "other",
}

_U_OPEN = {
    **_U_MET,
    "question_type": "open",
}

_U_STMT = {
    **_U_MET,
    "question_type": "statement",
}

_U_EMP = {
    "empathy": {"empathy_score": 4.0, "found_keywords": ["understand", "sense"], "has_empathy": True},
    "question_type": "open",
    "tone": {"calm": True, "clear": True},
    "empathy_response": True,
    "empathy_response_type": "understanding",
}

_A_EO = {
    "empathy_opportunity_type": "explicit",
    "empathy_opportunity": True,
    "latency_ms": 1000.0,
}


def _eo(dimension: str, text: str, expl: str = "explicit") -> dict:
    return {
        "dimension": dimension,
        "explicit_or_implicit": expl,
        "text": text,
        "confidence": 0.85,
        "provenance": "fixture",
        "span_type": "eo",
    }


def _resp(kind: str, text: str) -> dict:
    return {
        "type": kind,
        "text": text,
        "confidence": 0.85,
        "provenance": "fixture",
        "span_type": "response",
    }


TEST_DIFFICULT_DIAGNOSIS_STRONG = {
    "name": "difficult_diagnosis_strong",
    "label": "DIFFICULT_DIAGNOSIS_STRONG",
    "transcript": [
        {
            "role": "user",
            "turn_number": 1,
            "text": (
                "Hi, thank you for coming in today. Before we begin, is this a comfortable "
                "place to talk, or would you prefer somewhere more private?"
            ),
            "metrics_json": _U_OPEN,
            "spans_json": [],
            "expected_spikes": "setting",
        },
        {
            "role": "assistant",
            "turn_number": 2,
            "text": "No, this is fine… I've just been really anxious about these results.",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "anxious")],
        },
        {
            "role": "user",
            "turn_number": 3,
            "text": (
                "I can understand that this has been weighing on you. Can you tell me what "
                "you've been thinking or what concerns you most?"
            ),
            "metrics_json": _U_EMP,
            "spans_json": [
                _resp("understanding", "I can understand that this has been weighing on you"),
            ],
            "relations_json": [
                {
                    "source_turn_number": 2,
                    "target_turn_number": 3,
                    "source_span_type": "eo",
                    "target_span_type": "response",
                    "relation": "addressed_by",
                }
            ],
            "expected_spikes": "perception",
        },
        {
            "role": "assistant",
            "turn_number": 4,
            "text": "I just keep thinking it could be something really serious… like cancer.",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "serious", "implicit"), _eo("Appreciation", "cancer", "implicit")],
        },
        {
            "role": "user",
            "turn_number": 5,
            "text": (
                "That's a very real and understandable fear. Before I go into the results, "
                "would you like me to explain everything in detail, or would you prefer a "
                "high-level overview first?"
            ),
            "metrics_json": _U_EMP,
            "spans_json": [
                _resp("understanding", "That's a very real and understandable fear"),
            ],
            "relations_json": [
                {
                    "source_turn_number": 4,
                    "target_turn_number": 5,
                    "source_span_type": "eo",
                    "target_span_type": "response",
                    "relation": "addressed_by",
                }
            ],
            "expected_spikes": "invitation",
        },
        {
            "role": "assistant",
            "turn_number": 6,
            "text": "I think I want to know everything.",
            "metrics_json": {**_A_EO, "empathy_opportunity": False},
            "spans_json": [],
        },
        {
            "role": "user",
            "turn_number": 7,
            "text": (
                "Okay. Based on the tests, there are findings that are concerning for cancer. "
                "I know that's difficult to hear."
            ),
            "metrics_json": _U_STMT,
            "spans_json": [],
            "expected_spikes": "knowledge",
        },
        {
            "role": "assistant",
            "turn_number": 8,
            "text": "So… it really is cancer?",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "cancer", "implicit")],
        },
        {
            "role": "user",
            "turn_number": 9,
            "text": (
                "We strongly suspect it, but we still need additional tests to confirm exactly "
                "what type and stage. I can see this is overwhelming—what's going through your "
                "mind right now?"
            ),
            "metrics_json": _U_EMP,
            "spans_json": [
                _resp("understanding", "I can see this is overwhelming"),
            ],
            "relations_json": [
                {
                    "source_turn_number": 8,
                    "target_turn_number": 9,
                    "source_span_type": "eo",
                    "target_span_type": "response",
                    "relation": "addressed_by",
                }
            ],
            "expected_spikes": "emotion",
        },
        {
            "role": "assistant",
            "turn_number": 10,
            "text": "I'm just scared… I don't know what this means for my future.",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "scared")],
        },
        {
            "role": "user",
            "turn_number": 11,
            "text": (
                "That fear makes a lot of sense. Anyone in your position would feel that way. "
                "You're not alone in this—we're going to take this step by step together."
            ),
            "metrics_json": _U_EMP,
            "spans_json": [
                _resp("understanding", "That fear makes a lot of sense"),
            ],
            "relations_json": [
                {
                    "source_turn_number": 10,
                    "target_turn_number": 11,
                    "source_span_type": "eo",
                    "target_span_type": "response",
                    "relation": "addressed_by",
                }
            ],
            "expected_spikes": "emotion",
        },
        {
            "role": "assistant",
            "turn_number": 12,
            "text": "Okay…",
            "metrics_json": {**_A_EO, "empathy_opportunity": False},
            "spans_json": [],
        },
        {
            "role": "user",
            "turn_number": 13,
            "text": (
                "The next step is to run some additional tests to confirm the diagnosis and "
                "understand how best to treat it. Once we have that, we'll go over all your "
                "options together. How does that sound?"
            ),
            "metrics_json": _U_OPEN,
            "spans_json": [],
            "expected_spikes": "strategy",
        },
        {
            "role": "assistant",
            "turn_number": 14,
            "text": "That helps… I just need to process this.",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Appreciation", "helps", "implicit")],
        },
    ],
    "expected_feedback": {
        "notes": "Full SPIKES-consistent delivery with invitation and emotional validation.",
        "score_ranges": {
            "empathy_score": [20, 100],
            "overall_score": [15, 100],
            "spikes_completion_score": [80, 100],
        },
    },
}

TEST_DIFFICULT_DIAGNOSIS_DECENT = {
    "name": "difficult_diagnosis_decent_missing_invitation",
    "label": "DIFFICULT_DIAGNOSIS_DECENT",
    "transcript": [
        {
            "role": "user",
            "turn_number": 1,
            "text": "Hi, thanks for coming in. I know you've been waiting for these results.",
            "metrics_json": _U_STMT,
            "spans_json": [],
            "expected_spikes": "setting",
        },
        {
            "role": "assistant",
            "turn_number": 2,
            "text": "Yeah… I've been really worried.",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "worried")],
        },
        {
            "role": "user",
            "turn_number": 3,
            "text": "That's understandable. These situations can be stressful.",
            "metrics_json": _U_EMP,
            "spans_json": [_resp("understanding", "That's understandable")],
            "relations_json": [
                {
                    "source_turn_number": 2,
                    "target_turn_number": 3,
                    "source_span_type": "eo",
                    "target_span_type": "response",
                    "relation": "addressed_by",
                }
            ],
            "expected_spikes": "perception",
        },
        {
            "role": "assistant",
            "turn_number": 4,
            "text": "I keep thinking it might be cancer.",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "cancer", "implicit")],
        },
        {
            "role": "user",
            "turn_number": 5,
            "text": "I understand why you'd think that. The results do show something concerning.",
            "metrics_json": _U_EMP,
            "spans_json": [_resp("understanding", "I understand why you'd think that")],
            "relations_json": [
                {
                    "source_turn_number": 4,
                    "target_turn_number": 5,
                    "source_span_type": "eo",
                    "target_span_type": "response",
                    "relation": "addressed_by",
                }
            ],
            # Skips explicit invitation stage in SPIKES progression
            "expected_spikes": "knowledge",
        },
        {
            "role": "assistant",
            "turn_number": 6,
            "text": "What do you mean?",
            "metrics_json": {**_A_EO, "empathy_opportunity": False},
            "spans_json": [],
        },
        {
            "role": "user",
            "turn_number": 7,
            "text": (
                "The findings suggest that this could be cancer, although we need further "
                "tests to confirm."
            ),
            "metrics_json": _U_STMT,
            "spans_json": [],
            "expected_spikes": "knowledge",
        },
        {
            "role": "assistant",
            "turn_number": 8,
            "text": "That's really scary.",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "scary")],
        },
        {
            "role": "user",
            "turn_number": 9,
            "text": "I can see how frightening that is. We're going to work through this together.",
            "metrics_json": _U_EMP,
            "spans_json": [_resp("understanding", "I can see how frightening that is")],
            "relations_json": [
                {
                    "source_turn_number": 8,
                    "target_turn_number": 9,
                    "source_span_type": "eo",
                    "target_span_type": "response",
                    "relation": "addressed_by",
                }
            ],
            "expected_spikes": "emotion",
        },
        {
            "role": "assistant",
            "turn_number": 10,
            "text": "Okay…",
            "metrics_json": {**_A_EO, "empathy_opportunity": False},
            "spans_json": [],
        },
        {
            "role": "user",
            "turn_number": 11,
            "text": (
                "We'll arrange further testing and then discuss treatment options once we have "
                "more clarity."
            ),
            "metrics_json": _U_STMT,
            "spans_json": [],
            "expected_spikes": "strategy",
        },
        {
            "role": "assistant",
            "turn_number": 12,
            "text": "Alright.",
            "metrics_json": {**_A_EO, "empathy_opportunity": False},
            "spans_json": [],
        },
    ],
    "expected_feedback": {
        "notes": "Omits explicit invitation for patient information preference before news.",
        "score_ranges": {
            "empathy_score": [15, 95],
            "spikes_completion_score": [60, 95],
        },
    },
}

TEST_DIFFICULT_DIAGNOSIS_MIXED = {
    "name": "difficult_diagnosis_mixed_missed_emotion",
    "label": "DIFFICULT_DIAGNOSIS_MIXED",
    "transcript": [
        {
            "role": "user",
            "turn_number": 1,
            "text": "Hi, thanks for coming in today. Let's go over your results.",
            "metrics_json": _U_STMT,
            "spans_json": [],
            "expected_spikes": "setting",
        },
        {
            "role": "assistant",
            "turn_number": 2,
            "text": "I've been really nervous about this.",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "nervous")],
        },
        {
            "role": "user",
            "turn_number": 3,
            "text": "Okay. The results show something concerning that we need to investigate further.",
            "metrics_json": _U_STMT,
            "spans_json": [],
            "expected_spikes": "perception",
        },
        {
            "role": "assistant",
            "turn_number": 4,
            "text": "Like cancer?",
            "metrics_json": {**_A_EO, "empathy_opportunity": False},
            "spans_json": [],
        },
        {
            "role": "user",
            "turn_number": 5,
            "text": "Yes, that is a possibility based on what we see.",
            "metrics_json": _U_STMT,
            "spans_json": [],
            "expected_spikes": "knowledge",
        },
        {
            "role": "assistant",
            "turn_number": 6,
            "text": "I'm really scared… I don't know what I'll do.",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "scared")],
        },
        {
            # Missed empathy: jumps to logistics without addressing fear
            "role": "user",
            "turn_number": 7,
            "text": "We'll need to schedule additional diagnostic tests to confirm the findings.",
            "metrics_json": _U_MET,
            "spans_json": [],
            "expected_spikes": "knowledge",
        },
        {
            "role": "assistant",
            "turn_number": 8,
            "text": "Okay…",
            "metrics_json": {**_A_EO, "empathy_opportunity": False},
            "spans_json": [],
        },
        {
            "role": "user",
            "turn_number": 9,
            "text": "After that, we'll discuss treatment options depending on the results.",
            "metrics_json": _U_STMT,
            "spans_json": [],
            "expected_spikes": "strategy",
        },
        {
            "role": "assistant",
            "turn_number": 10,
            "text": "This is a lot…",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Appreciation", "lot", "implicit")],
        },
        {
            "role": "user",
            "turn_number": 11,
            "text": "Yes, it is a lot of information. Do you have any questions about the process?",
            "metrics_json": _U_OPEN,
            "spans_json": [],
            "expected_spikes": "strategy",
        },
        {
            "role": "assistant",
            "turn_number": 12,
            "text": "Not right now.",
            "metrics_json": {**_A_EO, "empathy_opportunity": False},
            "spans_json": [],
        },
    ],
    "expected_feedback": {
        "notes": "Jumps to results; weak response to explicit fear at turn 6.",
        "score_ranges": {
            "empathy_score": [5, 85],
            "spikes_completion_score": [50, 95],
        },
    },
}

TEST_DIFFICULT_DIAGNOSIS_WEAK = {
    "name": "difficult_diagnosis_weak",
    "label": "DIFFICULT_DIAGNOSIS_WEAK",
    "transcript": [
        {
            "role": "user",
            "turn_number": 1,
            "text": "Hi. I have your results.",
            "metrics_json": _U_STMT,
            "spans_json": [],
            "expected_spikes": "setting",
        },
        {
            "role": "assistant",
            "turn_number": 2,
            "text": "Okay… I've been worried.",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "worried")],
        },
        {
            "role": "user",
            "turn_number": 3,
            "text": "The scan shows abnormal findings consistent with possible malignancy.",
            "metrics_json": _U_MET,
            "spans_json": [],
        },
        {
            "role": "assistant",
            "turn_number": 4,
            "text": "Wait… are you saying I have cancer?",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "cancer", "implicit")],
        },
        {
            "role": "user",
            "turn_number": 5,
            "text": "It is likely, but we need further confirmation.",
            "metrics_json": _U_MET,
            "spans_json": [],
        },
        {
            "role": "assistant",
            "turn_number": 6,
            "text": "That's terrifying…",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "terrifying")],
        },
        {
            "role": "user",
            "turn_number": 7,
            "text": "We'll proceed with additional tests.",
            "metrics_json": _U_MET,
            "spans_json": [],
        },
        {
            "role": "assistant",
            "turn_number": 8,
            "text": "I don't even know what to say…",
            "metrics_json": _A_EO,
            "spans_json": [_eo("Feeling", "say", "implicit")],
        },
        {
            "role": "user",
            "turn_number": 9,
            "text": "You'll be referred to oncology after confirmation.",
            "metrics_json": _U_MET,
            "spans_json": [],
        },
        {
            "role": "assistant",
            "turn_number": 10,
            "text": "Okay…",
            "metrics_json": {**_A_EO, "empathy_opportunity": False},
            "spans_json": [],
        },
    ],
    "expected_feedback": {
        "notes": "Blunt delivery; minimal empathy and SPIKES structure.",
        "score_ranges": {
            "empathy_score": [0, 45],
            "overall_score": [0, 45],
            "spikes_completion_score": [0, 35],
        },
    },
}

ALL_DIFFICULT_DIAGNOSIS_FIXTURES = [
    TEST_DIFFICULT_DIAGNOSIS_STRONG,
    TEST_DIFFICULT_DIAGNOSIS_DECENT,
    TEST_DIFFICULT_DIAGNOSIS_MIXED,
    TEST_DIFFICULT_DIAGNOSIS_WEAK,
]
