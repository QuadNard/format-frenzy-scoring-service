# tests/test_dataset.py
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

DATA = [
  {
    "id": 1,
    "answer": "def square_all(numbers):\n    return list(map(lambda x: x**2, numbers))\n# Alternative: [x**2 for x in numbers]",
    "question": "Create a function that uses map to square each element in a list"
  },
  {
    "id": 2,
    "answer": "def sort_by_last_digit(numbers):\n    return sorted(numbers, key=lambda x: x % 10)",
    "question": "Implement a sorting function using the key parameter"
  },
  {
    "id": 3,
    "answer": "def get_even_numbers(numbers):\n    return list(filter(lambda x: x % 2 == 0, numbers))\n# Alternative: [x for x in numbers if x % 2 == 0]",
    "question": "Use filter to get only even numbers from a list"
  },
  {
    "id": 4,
    "answer": "def find_max(*args):\n    if not args:\n        return None\n    return max(args)",
    "question": "Create a function with *args to find the maximum value"
  },
  {
    "id": 5,
    "answer": "def format_user(**kwargs):\n    if 'name' not in kwargs:\n        return \"Anonymous\"\n    details = [f\"Name: {kwargs['name']}\"]\n    for key, value in kwargs.items():\n        if key != 'name':\n            details.append(f\"{key.capitalize()}: {value}\")\n    return \", \".join(details)",
    "question": "Write a function with **kwargs that creates a formatted string"
  },
  {
    "id": 6,
    "answer": "def interleave(list1, list2):\n    result = []\n    for a, b in zip(list1, list2):\n        result.extend([a, b])\n    return result\n# Alternative: [item for pair in zip(list1, list2) for item in pair]",
    "question": "Use zip to interleave two lists"
  },
  {
    "id": 7,
    "answer": "def factorial(n):\n    if n < 0:\n        raise ValueError(\"n must be non-negative\")\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
    "question": "Create a recursive function for factorial (with negative-n guard)"
  },
  {
    "id": 8,
    "answer": "def find_all_indices(items, target):\n    return [i for i, item in enumerate(items) if item == target]",
    "question": "Use enumerate to find indices of all occurrences of an element"
  },
  {
    "id": 9,
    "answer": "from functools import wraps\n\ndef memoize(func):\n    cache = {}\n    @wraps(func)\n    def wrapper(*args, **kwargs):\n        key = (args, tuple(sorted(kwargs.items())))\n        if key not in cache:\n            cache[key] = func(*args, **kwargs)\n        return cache[key]\n    return wrapper\n\n@memoize\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
    "question": "Implement a memoization decorator (handling both *args & **kwargs)"
  },
  {
    "id": 10,
    "answer": "def has_any_negatives(numbers):\n    return any(num < 0 for num in numbers)\n\ndef all_are_positive(numbers):\n    return all(num > 0 for num in numbers)",
    "question": "Use any/all with generator expressions"
  }
]

def test_bulk_dataset_exact_matches():
    # 1) Build payload for construct-answers
    construct_payload = [
        {"question_id": str(item["id"]), "correct_code": item["answer"]}
        for item in DATA
    ]
    r1 = client.post("/construct-answers", json=construct_payload)
    assert r1.status_code == 200
    ast_map = r1.json()
    # Ensure every ID is present
    assert set(ast_map.keys()) == {str(item["id"]) for item in DATA}

    # 2) For each item, check exact match
    for item in DATA:
        qid = str(item["id"])
        check_payload = {
            "question_id": qid,
            "user_code": item["answer"],
            "correct_ast": ast_map[qid]
        }
        r2 = client.post("/check-answer", json=check_payload)
        assert r2.status_code == 200, f"Failed for qid={qid}: {r2.text}"
        resp = r2.json()
        assert resp["exact_match"] is True
        assert resp["score"] == 100.0
        # both messages “Perfect match!” and “Exact AST match!”
        # will satisfy this substring check
        assert "match" in resp["feedback"]["message"].lower()


def test_bulk_dataset_partial_credit():
    # Re-use the AST map
    construct_payload = [
        {"question_id": str(item["id"]), "correct_code": item["answer"]}
        for item in DATA
    ]
    ast_map = client.post("/construct-answers", json=construct_payload).json()

    # 1) Alter q1: replace map() with a list comprehension
    bad1 = DATA[0]["answer"].replace(
        "list(map(lambda x: x**2, numbers))",
        "[x**2 for x in numbers]"
    )
    payload1 = {
        "question_id": "1",
        "user_code": bad1,
        "correct_ast": ast_map["1"]
    }
    r_bad1 = client.post("/check-answer", json=payload1)
    assert r_bad1.status_code == 200
    res1 = r_bad1.json()
    assert res1["exact_match"] is False
    assert res1["score"] < 100.0
    assert res1["feedback"]["issues"]

    # 2) Alter q2: drop the key parameter entirely
    bad2 = "def sort_by_last_digit(numbers):\n    return sorted(numbers)"
    payload2 = {
        "question_id": "2",
        "user_code": bad2,
        "correct_ast": ast_map["2"]
    }
    r_bad2 = client.post("/check-answer", json=payload2)
    assert r_bad2.status_code == 200
    res2 = r_bad2.json()
    assert res2["exact_match"] is False
    assert res2["score"] < 100.0
    assert res2["feedback"]["issues"]