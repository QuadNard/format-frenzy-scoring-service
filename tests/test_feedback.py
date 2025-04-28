# test_main.py
from fastapi.testclient import TestClient
import pytest
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from src.main import app

client = TestClient(app)

# Sample question set
sample_questions = [
    {
        "id": 11,
        "question": "Count elements matching a condition",
        "correct_code": "def count_if(nums, condition):\n    return sum(1 for num in nums if condition(num))"
    },
    {
        "id": 12,
        "question": "Find the first element that satisfies a condition",
        "correct_code": "def find_first(nums, condition):\n    return next((num for num in nums if condition(num)), None)"
    },
    {
        "id": 13,
        "question": "Transform elements based on multiple conditions (FizzBuzz style)",
        "correct_code": "def transform(nums):\n    result = []\n    for num in nums:\n        if num % 3 == 0 and num % 5 == 0:\n            result.append(\"FizzBuzz\")\n        elif num % 3 == 0:\n            result.append(\"Fizz\")\n        elif num % 5 == 0:\n            result.append(\"Buzz\")\n        else:\n            result.append(str(num))\n    return result"
    }
]

# Slightly wrong user codes
sample_user_codes = {
    11: "def count_if(nums, condition):\n return sum(1 for num in nums if condition(num)",  # Missing )
    12: "def find_first(nums, condition):\n next((num for num in nums if condition(num)), None)",  # Missing return
    13: "def transform(nums):\n result = []\n for num in nums:\n if num % 3 == 0:\n result.append(\"Fizz\")\n else:\n result.append(str(num))"  # Incomplete FizzBuzz
}

@pytest.mark.parametrize("question", sample_questions)
def test_check_answer_partial_credit(question):
    user_code = sample_user_codes[question["id"]]
    
    payload = {
        "question_id": str(question["id"]),
        "user_code": user_code,
        "correct_code": question["correct_code"],
    }

    response = client.post("/check-answer", json=payload)

    # Debug print in case of future failures
    print(response.json())

    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"

    data = response.json()

    # Check important fields
    assert "exact_match" in data
    assert "score" in data
    assert "feedback" in data
    assert isinstance(data["score"], (int, float))
    assert isinstance(data["feedback"]["issues"], list)

    # Exact match should be False because user_code is slightly broken
    assert data["exact_match"] is False

    # Score should be greater than or equal to 0
    assert data["score"] >= 0

    print(f"\n✅ Test Passed | Question ID {question['id']} | Score: {data['score']} | Issues: {[i['message'] for i in data['feedback']['issues']]}")


