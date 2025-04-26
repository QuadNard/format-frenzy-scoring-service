from fastapi.testclient import TestClient
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from src.main import app, get_ast_dump

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message": "OK"}

def test_construct_answers_and_check_exact_match():
    # 1) construct AST for a simple function
    payload = [
        {"question_id": "q1", "correct_code": "def foo(x):\n    return x * 2"}
    ]
    resp = client.post("/construct-answers", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "q1" in data
    correct_ast = data["q1"]

    # 2) send identical code to /check-answer
    check_payload = {
        "question_id": "q1",
        "user_code": "def foo(x):\n    return x * 2",
        "correct_ast": correct_ast
    }
    resp2 = client.post("/check-answer", json=check_payload)
    assert resp2.status_code == 200
    result = resp2.json()
    assert result["exact_match"] is True
    assert result["score"] == 100.0
    assert "Perfect match" in result["feedback"]["message"]

def test_check_answer_syntax_error():
    # send malformed code
    check_payload = {
        "question_id": "q2",
        "user_code": "def bar(x)\n    return x",
        "correct_ast": ""  # won't be reached
    }
    resp = client.post("/check-answer", json=check_payload)
    assert resp.status_code == 400
    assert "Syntax error" in resp.json()["detail"]

def test_partial_match_feedback():
    # correct code has an if-statement, user omits it
    correct = "def f(x):\n    if x>0:\n        return x\n    return 0"
    ast_dump = get_ast_dump(correct)
    check_payload = {
        "question_id": "q3",
        "user_code": "def f(x):\n    return x",
        "correct_ast": ast_dump
    }
    resp = client.post("/check-answer", json=check_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["exact_match"] is False
    assert data["score"] < 100.0
    # we expect at least one issue about missing conditionals
    issues = data["feedback"]["issues"]
    messages = [i["message"] for i in issues]
    assert any("Missing conditional" in m for m in messages)