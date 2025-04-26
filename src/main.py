import difflib
import ast
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.schemas import (
    CheckAnswerRequest,
    CodeIssue,
    Feedback,
    ConstructAnswerItem,
    ScoreResponse,
)

from src.server.cruds import crud_router_v1
from src.ast_analyzer import find_missing_nodes

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(crud_router_v1, prefix="/v1")

@app.get("/")
async def root():
    return {"message": "OK"}


def get_ast_dump(src: str) -> str:
    """Parse source into AST dump (no attributes) or raise HTTPException."""
    try:
        tree = ast.parse(src)
        return ast.dump(tree, include_attributes=False)
    except SyntaxError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Syntax error on line {e.lineno}, col {e.offset}: {e.msg}"
        ) from e


def compare_ast(user_code: str,
                correct_code: str,
                user_dump: str,
                correct_dump:str) -> Dict[str, Any]:
    """Compute exact-match, percentage score, and structured issues with accurate line numbers."""
    if user_dump == correct_dump:
        return {"exact_match": True, "score": 100.0,
                "feedback": {"message": "Exact AST match!", "issues": []}}

    sim = difflib.SequenceMatcher(None, user_dump, correct_dump).ratio() * 100
    # Use the imported function
    issues = find_missing_nodes(user_code, correct_code)
    # If no specific issues found, provide a general similarity message
    if not issues:
        issues = [{
            "line_number": 1,
            "column": None,
            "end_line_number": None,
            "end_column": None,
            "message": "Code structure differs from expected solution"
        }]
    score = max(10.0, sim - len(issues) * 10)

    return {
        "exact_match": False,
        "score": score,
        "feedback": {
            "message": f"AST similarity: {sim:.1f}%",
            "issues": issues
        }
    }


@app.post("/construct-answers", response_model=Dict[str, Any])
async def construct_answers(items: List[ConstructAnswerItem]):
    return {
        item.question_id: get_ast_dump(item.correct_code)
        for item in items
    }


@app.post("/check-answer", response_model=ScoreResponse)
async def check_answer(req: CheckAnswerRequest):
    user_dump = get_ast_dump(req.user_code)
    comparison = compare_ast(req.user_code, req.correct_code, user_dump, req.correct_ast)
    return ScoreResponse(
        exact_match=comparison["exact_match"],
        score=comparison["score"],
        feedback=Feedback(
            message=comparison["feedback"]["message"],
            issues=[CodeIssue(**i) for i in comparison["feedback"]["issues"]]
        )
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
