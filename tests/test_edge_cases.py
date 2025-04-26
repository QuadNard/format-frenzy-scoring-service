from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_construct_answers_invalid_body():
    # payload must be a list, not a dict
    r = client.post("/construct-answers", json={"foo": "bar"})
    assert r.status_code == 422


def test_construct_answers_missing_field():
    # each item needs both question_id and correct_code
    r = client.post("/construct-answers", json=[{"question_id": "x"}])
    assert r.status_code == 422


def test_construct_answers_syntax_error():
    # malformed Python in correct_code should yield 400
    bad = "def broken:\n    pass"
    r = client.post("/construct-answers", json=[{"question_id": "e1", "correct_code": bad}])
    assert r.status_code == 400
    assert "Syntax error" in r.json()["detail"]


def test_check_answer_invalid_body():
    # payload must include question_id, user_code, and correct_ast
    r = client.post("/check-answer", json={"user_code": "def foo(): pass"})
    assert r.status_code == 422


def test_check_answer_syntax_error_user_code():
    # first get a valid AST for a simple function
    valid = "def foo():\n    return 1"
    ast_map = client.post("/construct-answers", json=[{"question_id": "c1", "correct_code": valid}]).json()
    # now send malformed user_code
    r = client.post(
        "/check-answer",
        json={
            "question_id": "c1",
            "user_code": "def foo() return 1",
            "correct_ast": ast_map["c1"]
        }
    )
    assert r.status_code == 400
    assert "Syntax error" in r.json()["detail"]


def test_empty_function_exact_match():
    code = "def foo():\n    pass"
    ast_map = client.post("/construct-answers", json=[{"question_id": "e2", "correct_code": code}]).json()
    r = client.post("/check-answer", json={
        "question_id": "e2",
        "user_code": code,
        "correct_ast": ast_map["e2"]
    })
    assert r.status_code == 200
    resp = r.json()
    assert resp["exact_match"] is True
    assert resp["score"] == 100.0


def test_deeply_nested_structure():
    code = """def foo(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                print(i)
    else:
        print("none")
"""
    ast_map = client.post("/construct-answers", json=[{"question_id": "d1", "correct_code": code}]).json()
    r = client.post("/check-answer", json={
        "question_id": "d1",
        "user_code": code,
        "correct_ast": ast_map["d1"]
    })
    assert r.status_code == 200
    assert r.json()["exact_match"] is True


def test_large_snippet_performance_and_exact_match():
    # generate 100 simple funcs
    code = "\n".join(f"def f{i}(x): return x + {i}" for i in range(100))
    ast_map = client.post("/construct-answers", json=[{"question_id": "l1", "correct_code": code}]).json()
    r = client.post("/check-answer", json={
        "question_id": "l1",
        "user_code": code,
        "correct_ast": ast_map["l1"]
    })
    assert r.status_code == 200
    assert r.json()["exact_match"] is True


def test_partial_credit_missing_return():
    # correct version returns x*2, user omits return
    correct = "def foo(x):\n    return x * 2"
    ast_map = client.post("/construct-answers", json=[{"question_id": "p1", "correct_code": correct}]).json()
    bad = "def foo(x):\n    x * 2"
    r = client.post("/check-answer", json={
        "question_id": "p1",
        "user_code": bad,
        "correct_ast": ast_map["p1"]
    })
    assert r.status_code == 200
    res = r.json()
    assert res["exact_match"] is False
    assert res["score"] < 100.0
    # should report missing return
    msgs = [iss["message"] for iss in res["feedback"]["issues"]]
    assert any("Missing return" in m for m in msgs)
