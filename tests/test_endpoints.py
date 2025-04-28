# tests/test_main.py
import pytest
from fastapi.testclient import TestClient
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from src.main import app

client = TestClient(app)

# Sample data for construct-answers
construct_payload = [
    {
        "question_id": "11",
        "correct_code": "def count_if(nums, condition):\n    return sum(1 for num in nums if condition(num))"
    },
    {
        "question_id": "12",
        "correct_code": "def find_first(nums, condition):\n    return next((num for num in nums if condition(num)), None)"
    },
]

# Sample user code submissions (one exact, one slightly wrong)
sample_submissions = [
    {
        "question_id": "11",
        "user_code": "def count_if(nums, condition):\n    return sum(1 for num in nums if condition(num))",  # perfect match
        "correct_code": "def count_if(nums, condition):\n    return sum(1 for num in nums if condition(num))"
    },
    {
        "question_id": "12",
        "user_code": "def find_first(nums, condition):\n next((num for num in nums if condition(num)), None)",  # missing 'return'
        "correct_code": "def find_first(nums, condition):\n    return next((num for num in nums if condition(num)), None)"
    }
]

def test_root_ok():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "OK"}

def test_construct_answers():
    response = client.post("/construct-answers", json=construct_payload)
    assert response.status_code == 200

    data = response.json()
    assert "11" in data
    assert "12" in data

    # Should return AST dumps as strings
    assert isinstance(data["11"], str)
    assert isinstance(data["12"], str)

@pytest.mark.parametrize("submission", sample_submissions)
def test_check_answer(submission):
    payload = {
        "question_id": submission["question_id"],
        "user_code": submission["user_code"],
        "correct_code": submission["correct_code"],
    }

    response = client.post("/check-answer", json=payload)
    assert response.status_code == 200

    data = response.json()

    assert "exact_match" in data
    assert "score" in data
    assert "feedback" in data

    if submission["user_code"].strip() == submission["correct_code"].strip():
        assert data["exact_match"] is True
        assert data["score"] == 27.0
    else:
        assert data["exact_match"] is False
        assert data["score"] >= 0

    print(f"\n✅ Check Answer | Question {submission['question_id']} | Score: {data['score']} | Issues: {[i['message'] for i in data['feedback']['issues']]}")
