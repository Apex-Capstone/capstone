from services.stage_tracker import StageTracker


def test_perception_detection():
    """Perception stage is detected from phrases like 'what do you know'."""
    tracker = StageTracker()

    text = "What do you know about the results?"

    stage = tracker.detect_stage(text, None)

    assert stage == "perception"


def test_invitation_detection():
    """Invitation stage is detected from phrases like 'would you like more details'."""
    tracker = StageTracker()

    text = "Would you like more details?"

    stage = tracker.detect_stage(text, None)

    assert stage == "invitation"