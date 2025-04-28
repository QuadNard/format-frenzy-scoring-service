# tests/test_garbage_code.py
import pytest
from fastapi.testclient import TestClient
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from src.main import app

client = TestClient(app)

# Garbage code samples
garbage_codes = [
    "this is not even python code!",
    "return)))))",
    "print('hello'",
    "def broken: pass",
    "if if if else else return"  # totally nonsensical
]

@pytest.mark.parametrize("garbage_code", garbage_codes)
def test_check_answer_with_garbage(garbage_code):
    payload = {
        "question_id": "999",  # fake ID
        "user_code": garbage_code,
        "correct_code": "def dummy():\n    pass",  # Any valid dummy correct code
    }

    response = client.post("/check-answer", json=payload)
    assert response.status_code == 200

    data = response.json()

    assert "exact_match" in data
    assert "score" in data
    assert "feedback" in data

    # Garbage should never be an exact match
    assert data["exact_match"] is False

    # Score should be very low or negative
    assert data["score"] <= 0

    # Feedback should mention "nonsensical" or "unrecognizable"
    feedback_messages = [issue["message"].lower() for issue in data["feedback"]["issues"]]
    matching_feedback = any(
        "nonsensical" in msg or "unrecognizable" in msg for msg in feedback_messages
    )
    assert matching_feedback, f"Expected feedback to mention 'nonsensical' or 'unrecognizable', got {feedback_messages}"

    print(f"\n✅ Garbage Code Test | Score: {data['score']} | Feedback: {[i['message'] for i in data['feedback']['issues']]}")
