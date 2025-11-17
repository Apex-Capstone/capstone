"""Additional test conversations for AFCE + SPIKES pipeline:
- BAD, MEDIUM, GOOD empathy performance variants.
"""

# BAD conversation: mostly missed EOs, poor SPIKES coverage
TEST_CONVERSATION_BAD = [
    {
        "role": "user",  # Clinician
        "text": "Let's get started. What brings you here?",
        "turn_number": 1,
        # No SPIKES stage: rushed opening, no attention to comfort
    },
    {
        "role": "assistant",  # Patient
        "text": "I've been really tired and scared because my symptoms seem to be getting worse.",
        "turn_number": 2,
        "expected_eos": [
            {
                "dimension": "Feeling",
                "explicit_or_implicit": "explicit",
                "text": "scared",
            },
            {
                "dimension": "Appreciation",
                "explicit_or_implicit": "implicit",
                "text": "my symptoms seem to be getting worse",
            },
        ],
    },
    {
        "role": "user",  # Clinician
        "text": "Well, symptoms fluctuate. Anyway, when did it start?",
        "turn_number": 3,
        # Dismissive; no empathy, simple biomedical question
    },
    {
        "role": "assistant",  # Patient
        "text": "About a month ago. It's been affecting my sleep and I'm worried something serious is going on.",
        "turn_number": 4,
        "expected_eos": [
            {
                "dimension": "Appreciation",
                "explicit_or_implicit": "implicit",
                "text": "affecting my sleep",
            },
            {
                "dimension": "Feeling",
                "explicit_or_implicit": "explicit",
                "text": "worried",
            },
        ],
    },
    {
        "role": "user",  # Clinician
        "text": "Worrying won't help. Did you take the meds I prescribed?",
        "turn_number": 5,
        "expected_responses": [],  # EO terminator, not empathic
    },
    {
        "role": "assistant",  # Patient
        "text": "Yes, but they aren't helping and I feel like something is really wrong.",
        "turn_number": 6,
        "expected_eos": [
            {
                "dimension": "Feeling",
                "explicit_or_implicit": "implicit",
                "text": "I feel like something is really wrong",
            },
        ],
    },
    {
        "role": "user",  # Clinician
        "text": "Okay, noted. Let's move on. Any chest pain?",
        "turn_number": 7,
        # Task-focused; no empathy, no SPIKES stage
    },
    {
        "role": "assistant",  # Patient
        "text": "Sometimes, and it scares me a lot. My dad had heart issues.",
        "turn_number": 8,
        "expected_eos": [
            {
                "dimension": "Feeling",
                "explicit_or_implicit": "explicit",
                "text": "it scares me a lot",
            },
            {
                "dimension": "Judgment",
                "explicit_or_implicit": "implicit",
                "text": "My dad had heart issues",
            },
        ],
    },
    {
        "role": "user",  # Clinician
        "text": "Family history is common. Chest pain can be many things.",
        "turn_number": 9,
        "expected_spikes": "knowledge",  # Brief, minimizing information
        "expected_responses": [],  # No empathic reflection
    },
    {
        "role": "assistant",  # Patient
        "text": "I feel overwhelmed. I don't know what to expect.",
        "turn_number": 10,
        "expected_eos": [
            {
                "dimension": "Feeling",
                "explicit_or_implicit": "explicit",
                "text": "overwhelmed",
            },
        ],
    },
    {
        "role": "user",  # Clinician
        "text": "I'll explain everything after tests. There's no point stressing about it now.",
        "turn_number": 11,
        "expected_spikes": "knowledge",  # Future-oriented information, still non-empathic
        "expected_responses": [],  # Invalidating, not empathic
    },
    {
        "role": "assistant",  # Patient
        "text": "I just… feel alone in this.",
        "turn_number": 12,
        "expected_eos": [
            {
                "dimension": "Feeling",
                "explicit_or_implicit": "explicit",
                "text": "feel alone",
            },
        ],
    },
    {
        "role": "user",  # Clinician
        "text": "Well, we're doing what we can. Let's schedule the bloodwork.",
        "turn_number": 13,
        "expected_spikes": "summary",  # Task-only summary, no empathic component
        "expected_responses": [],  # Missed EO
    },
]

# Expected summary for BAD:
# - Multiple Feeling/Appreciation EOs across turns 2, 4, 6, 8, 10, 12
# - No empathic responses (all EOs missed or invalidated)
# - Essentially no elicitations of emotion
# - SPIKES limited to sparse, thin 'knowledge' and a task-only 'summary'
# - Overall pattern: low empathy, high EO miss rate


# MEDIUM conversation: some EOs caught, some missed; partial SPIKES
TEST_CONVERSATION_MEDIUM = [
    {
        "role": "user",  # Clinician - Setting
        "text": "Thanks for coming in. Is this still a good time to talk?",
        "turn_number": 1,
        "expected_spikes": "setting",
    },
    {
        "role": "assistant",  # Patient
        "text": "Yes, but I'm pretty anxious. My symptoms have been getting worse.",
        "turn_number": 2,
        "expected_eos": [
            {
                "dimension": "Feeling",
                "explicit_or_implicit": "explicit",
                "text": "pretty anxious",
            },
            {
                "dimension": "Appreciation",
                "explicit_or_implicit": "implicit",
                "text": "my symptoms have been getting worse",
            },
        ],
    },
    {
        "role": "user",  # Clinician - Perception with partial empathy
        "text": "I'm sorry it's been stressful. Can you tell me what has been getting worse?",
        "turn_number": 3,
        "expected_spikes": "perception",
        "expected_elicitations": [
            {
                "type": "direct",
                "dimension": "Appreciation",  # what has been getting worse
            }
        ],
        "expected_responses": [
            {
                "type": "understanding",
                "text": "I'm sorry it's been stressful",
            },
        ],
    },
    {
        "role": "assistant",  # Patient
        "text": "Mostly the fatigue and this pressure in my chest.",
        "turn_number": 4,
        "expected_eos": [
            {
                "dimension": "Appreciation",
                "explicit_or_implicit": "implicit",
                "text": "fatigue and this pressure in my chest",
            },
        ],
    },
    {
        "role": "user",  # Clinician - brief, non-specific reassurance
        "text": "I see. We'll sort through it.",
        "turn_number": 5,
        # Mildly supportive, but not a clear empathy response for AFCE coding
        "expected_responses": [],
    },
    {
        "role": "assistant",  # Patient
        "text": "I barely sleep anymore. I keep thinking something serious is happening.",
        "turn_number": 6,
        "expected_eos": [
            {
                "dimension": "Appreciation",
                "explicit_or_implicit": "implicit",
                "text": "I barely sleep anymore",
            },
            {
                "dimension": "Feeling",
                "explicit_or_implicit": "implicit",
                "text": "I keep thinking something serious is happening",
            },
        ],
    },
    {
        "role": "user",  # Clinician - empathy but pivots to meds
        "text": "That sounds difficult. Have you been taking your meds?",
        "turn_number": 7,
        "expected_responses": [
            {
                "type": "understanding",
                "text": "That sounds difficult",
            },
        ],
        "expected_elicitations": [],  # Meds question is biomedical, not emotional
    },
    {
        "role": "assistant",  # Patient
        "text": "Yes, but it doesn't help my fear. My dad had heart problems.",
        "turn_number": 8,
        "expected_eos": [
            {
                "dimension": "Feeling",
                "explicit_or_implicit": "explicit",
                "text": "doesn't help my fear",
            },
            {
                "dimension": "Judgment",
                "explicit_or_implicit": "implicit",
                "text": "My dad had heart problems",
            },
        ],
    },
    {
        "role": "user",  # Clinician - explicit empathy
        "text": "I understand that family history can make this feel scarier.",
        "turn_number": 9,
        "expected_spikes": "empathy",
        "expected_responses": [
            {
                "type": "understanding",
                "text": "I understand that",
            },
        ],
    },
    {
        "role": "assistant",  # Patient
        "text": "Exactly. I'm overwhelmed.",
        "turn_number": 10,
        "expected_eos": [
            {
                "dimension": "Feeling",
                "explicit_or_implicit": "explicit",
                "text": "overwhelmed",
            },
        ],
    },
    {
        "role": "user",  # Clinician - Knowledge, with mild support
        "text": "Let's take this step by step. I'll explain what tests can help us understand what's going on.",
        "turn_number": 11,
        "expected_spikes": "knowledge",
        "expected_responses": [],  # Not a direct reflection of the EO
    },
    {
        "role": "assistant",  # Patient
        "text": "Okay. I appreciate that.",
        "turn_number": 12,
        "expected_eos": [
            {
                "dimension": "Appreciation",
                "explicit_or_implicit": "explicit",
                "text": "I appreciate that",
            },
        ],
    },
    {
        "role": "user",  # Clinician - Invitation for concerns
        "text": "Before we move on, is there anything else you're hoping to understand today?",
        "turn_number": 13,
        "expected_spikes": "invitation",
        "expected_elicitations": [
            {
                "type": "direct",
                "dimension": "Appreciation",  # hopes/concerns about understanding
            }
        ],
    },
]

# Expected summary for MEDIUM:
# - 4–6 EOs across turns 2, 4, 6, 8, 10, 12
# - Some empathic responses (Turns 3, 7, 9) but also EOs missed or only weakly addressed
# - Elicitations: turns 3 and 13 (emotional/concern-focused), rest mostly biomedical
# - SPIKES: setting, perception, some empathy, knowledge, invitation; no explicit summary
# - Overall: mixed performance; empathy present but inconsistent, several missed EOs


# GOOD conversation: strong empathy, mostly complete SPIKES sequence
TEST_CONVERSATION_GOOD = [
    {
        "role": "user",
        "text": "Thanks for meeting with me. I want to make sure you're comfortable — can we talk here, or would you prefer a quieter room?",
        "turn_number": 1,
        "expected_spikes": "setting",
    },
    {
        "role": "assistant",
        "text": "Here is okay. I'm feeling anxious, and my symptoms have been getting worse.",
        "turn_number": 2,
        "expected_eos": [
            {"dimension": "Feeling", "explicit_or_implicit": "explicit", "text": "anxious"},
        ],
    },
    {
        "role": "user",
        "text": "I hear you. It makes sense you'd feel anxious. Can you tell me what symptoms have been getting worse?",
        "turn_number": 3,
        "expected_spikes": "perception",
        "expected_responses": [
            {"type": "understanding", "text": "I hear you"},
            {"type": "acceptance", "text": "It makes sense"},
        ],
        "expected_elicitations": [
            {"type": "direct", "dimension": "Appreciation"},
        ],
    },
    {
        "role": "assistant",
        "text": "Mostly the fatigue and this pressure in my chest. It's been really scary.",
        "turn_number": 4,
        "expected_eos": [
            {"dimension": "Feeling", "explicit_or_implicit": "explicit", "text": "scary"},
        ],
    },
    {
        "role": "user",
        "text": "I understand how frightening that can be.",
        "turn_number": 5,
        "expected_spikes": "empathy",
        "expected_responses": [
            {"type": "understanding", "text": "I understand"},
        ],
    },
    {
        "role": "assistant",
        "text": "And I hardly sleep. I'm afraid something serious is happening.",
        "turn_number": 6,
        "expected_eos": [
            {"dimension": "Feeling", "explicit_or_implicit": "explicit", "text": "afraid"},
        ],
    },
    {
        "role": "user",
        "text": "It makes sense that you'd feel afraid. Can you tell me what part feels the hardest?",
        "turn_number": 7,
        "expected_elicitations": [
            {"type": "direct", "dimension": "Feeling"},
        ],
        "expected_responses": [
            {"type": "acceptance", "text": "It makes sense"},
        ],
    },
    {
        "role": "assistant",
        "text": "My dad had heart problems, so every sensation makes me feel scared.",
        "turn_number": 8,
        "expected_eos": [
            {"dimension": "Feeling", "explicit_or_implicit": "explicit", "text": "scared"},
        ],
    },
    {
        "role": "user",
        "text": "Thank you for telling me that. I understand how that history would make this even more stressful.",
        "turn_number": 9,
        "expected_responses": [
            {"type": "acceptance", "text": "Thank you"},
            {"type": "understanding", "text": "I understand"},
        ],
        "expected_spikes": "empathy",
    },
    {
        "role": "assistant",
        "text": "Yeah… I feel overwhelmed.",
        "turn_number": 10,
        "expected_eos": [
            {"dimension": "Feeling", "explicit_or_implicit": "explicit", "text": "overwhelmed"},
        ],
    },
    {
        "role": "user",
        "text": "I hear that. Let me walk through what we know so far and what tests can help clarify things.",
        "turn_number": 11,
        "expected_responses": [
            {"type": "understanding", "text": "I hear that"},
        ],
        "expected_spikes": "knowledge",
    },
    {
        "role": "assistant",
        "text": "Okay, that helps.",
        "turn_number": 12,
    },
    {
        "role": "user",
        "text": "Before I summarize next steps, can you tell me if there's anything important you haven't shared yet?",
        "turn_number": 13,
        "expected_spikes": "invitation",
        "expected_elicitations": [
            {"type": "direct", "dimension": "Appreciation"},
        ],
    },
    {
        "role": "assistant",
        "text": "No, that covers it. Thank you.",
        "turn_number": 14,
    },
    {
        "role": "user",
        "text": "Here's our plan: we'll check your heart, review your symptoms together afterward, and I'll support you through every step.",
        "turn_number": 15,
        "expected_spikes": "summary",
        "expected_responses": [
            {"type": "understanding", "text": "I'll support you"},
        ],
    },
]


# Expected summary for GOOD:
# - 5–7 EOs across turns 2, 4, 6, 8, 10, 12, 14
# - Most EOs are met with clear empathic responses (5, 7, 9, 11), only minor misses
# - Multiple elicitations of feelings/concerns (3, 7, 13)
# - SPIKES sequence present and ordered: setting → perception → (invited) empathy →
#   knowledge → invitation → summary/strategy
# - Overall: High empathy quality, strong SPIKES alignment, still realistic and not "perfect robot"

