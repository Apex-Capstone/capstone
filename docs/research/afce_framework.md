# AFCE Framework and NLU Requirements

## 1. Purpose of the AFCE Framework

The **Appraisal Framework for Clinical Empathy (AFCE)** is a linguistic framework used to identify emotional expressions in clinical conversations.

It provides a structured way to detect when a patient expresses an emotional cue that may require an empathic response from the clinician.

The APEX system implements this framework to:

* detect emotional cues in patient statements
* identify empathy opportunities
* evaluate clinician responses
* provide feedback on communication performance

The AFCE framework is used as the **foundation of the Natural Language Understanding (NLU) layer** of the system.

---

# 2. AFCE Emotional Dimensions

The AFCE framework categorizes emotional expressions into three dimensions.

## 2.1 Feeling

Feeling expressions describe a patient's emotional state.

Examples:

```
"I'm scared."
"I'm worried."
"I'm overwhelmed."
"I feel anxious."
"This is frightening."
```

Characteristics:

* explicit emotional language
* direct expression of feelings
* often uses words describing emotional states

Typical keywords:

```
scared
afraid
worried
anxious
nervous
overwhelmed
terrified
frightened
```

---

## 2.2 Judgment

Judgment expressions evaluate the situation or express concern about outcomes.

Examples:

```
"This is terrible news."
"I don't know how I'm going to deal with this."
"This seems unfair."
"I can't believe this is happening."
```

Characteristics:

* evaluation of situation
* concern about consequences
* frustration or disbelief

Typical keywords:

```
terrible
unfair
can't handle
hopeless
awful
shocking
unexpected
```

---

## 2.3 Appreciation

Appreciation expressions describe the meaning or impact of the situation.

Examples:

```
"This is going to change my life."
"This will affect my family."
"This diagnosis changes everything."
"I never expected this."
```

Characteristics:

* reflection on life impact
* discussion of future implications
* interpretation of events

Typical keywords:

```
life changing
impact
family
future
everything
unexpected
```

---

# 3. Explicit vs Implicit Emotional Cues

AFCE distinguishes between **explicit** and **implicit** emotional expressions.

## Explicit Emotional Expressions

Explicit cues directly describe emotional states.

Examples:

```
"I'm scared."
"I'm worried."
"I'm really upset."
```

These are easier to detect using rule-based methods.

---

## Implicit Emotional Expressions

Implicit cues suggest emotional distress indirectly.

Examples:

```
"I don't know what to do."
"This is going to affect my family."
"I never expected something like this."
```

Implicit cues often require contextual interpretation.

They are typically detected using:

* keyword patterns
* phrase matching
* semantic interpretation

---

# 4. Empathy Opportunity Detection

An **Empathy Opportunity (EO)** occurs when a patient expresses an AFCE emotional cue.

The NLU layer must detect these opportunities during patient turns.

Example:

```
Patient: "I'm really scared about what this diagnosis means."
```

Detected AFCE span:

```
dimension: Feeling
explicit_or_implicit: explicit
text: "scared"
```

This span represents an **empathy opportunity**.

---

# 5. Empathic Response Types

Clinician responses to empathy opportunities can be categorized into three types.

## 5.1 Understanding

The clinician acknowledges the patient's emotional state.

Example:

```
"I understand this must be very difficult."
```

Typical keywords:

```
understand
I see
I can imagine
I hear you
```

---

## 5.2 Sharing

The clinician expresses emotional alignment with the patient.

Example:

```
"I can see why that would be frightening."
```

Typical keywords:

```
I can see why
I feel for you
I know this must be hard
```

---

## 5.3 Acceptance

The clinician validates the patient's feelings without judgment.

Example:

```
"It's completely understandable to feel that way."
```

Typical keywords:

```
that's understandable
it's normal to feel that way
anyone would feel that way
```

These responses represent **successful empathic communication**.

---

# 6. Elicitation

Clinicians can actively invite emotional expression from patients.

These are called **elicitation attempts**.

Examples:

```
"How are you feeling about this?"
"What concerns you the most right now?"
"What worries you about this diagnosis?"
```

Elicitation helps uncover empathy opportunities.

---

# 7. AFCE Span Detection in the APEX System

The APEX system uses **span detection** to identify AFCE elements in text.

Each detected span contains:

```
dimension
type
text
start_char
end_char
confidence
```

Span types include:

```
eo
elicitation
response
```

These spans are stored with each conversation turn.

Example span representation:

```
{
  span_type: "eo",
  dimension: "feeling",
  explicit_or_implicit: "explicit",
  text: "scared",
  start_char: 12,
  end_char: 18,
  confidence: 0.85
}
```

---

# 8. Linking AFCE Spans

During feedback evaluation, the system links spans to analyze interaction patterns.

Relationships include:

```
EO → Response
EO → Elicitation
EO → Missed Opportunity
```

Example:

```
Turn 3: EO detected
Turn 4: Response detected
```

This creates a relation:

```
EO_turn_3 → Response_turn_4
```

These relationships are used to evaluate clinician communication quality.

---

# 9. Role of AFCE in the APEX Architecture

The AFCE framework drives the design of the NLU system.

NLU responsibilities include detecting:

```
Empathy Opportunities
Empathic Responses
Elicitation Attempts
Question Types
Tone
```

These signals are passed to the dialogue manager and scoring engine.

---

# 10. AFCE Data Flow in the System

The AFCE analysis process follows this pipeline:

```
User or Patient Message
        ↓
NLU Processing
        ↓
AFCE Span Detection
        ↓
Span Storage (Turn.spans_json)
        ↓
Span Linking During Scoring
        ↓
Empathy Metrics
```

This architecture ensures that empathy detection and evaluation remain consistent with the research framework.

---

# 11. Summary

The AFCE framework provides a structured approach to identifying emotional expressions in clinical conversations.

By detecting emotional cues, elicitation attempts, and empathic responses, the APEX system can evaluate clinician communication performance and provide meaningful feedback.

The AFCE span detection system forms the foundation of the NLU layer and supports the feedback engine's empathy scoring methodology.

---

# Step 3 Complete

Your repo now contains:

```
docs/research/
    paper_analysis.md
    afce_framework.md
```

These two documents establish **the research foundation of your system**.
