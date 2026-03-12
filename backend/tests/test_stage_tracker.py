from services.stage_tracker import StageTracker


def test_perception_detection():
    tracker = StageTracker()

    text = "What do you understand about the results?"

    stage = tracker.detect_stage(text, None)

    assert stage == "perception"


def test_invitation_detection():
    tracker = StageTracker()

    text = "Would you like me to explain the diagnosis?"

    stage = tracker.detect_stage(text, None)

    assert stage == "invitation"