import difflib
import ast
from typing import List, Dict, Any
from contextlib import asynccontextmanager
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
from src.utils.error_logger import error_logger, log_error


app = FastAPI(
    lifespan=None
)

@asynccontextmanager
async def lifespan_handler(_: FastAPI):
    # Startup code (runs before first request)
    yield
    # Shutdown code (runs after server stops)
    error_logger.shutdown()

# Instantiate FastAPI with the lifespan handler
app = FastAPI(lifespan=lifespan_handler)

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


def compare_ast(user_dump: str, correct_dump: str) -> Dict[str, Any]:
    """Compute exact-match, percentage score, and structured issues."""
    if user_dump == correct_dump:
        return {
            "exact_match": True,
            "score": 100.0,
            "feedback": {"message": "Perfect match!", "issues": []}
        }

    sim = difflib.SequenceMatcher(None, user_dump, correct_dump).ratio() * 100
    issues: List[Dict[str, Any]] = []

    # Heuristic checks on dumps
    if user_dump.count("Return(") < correct_dump.count("Return("):
        issues.append({"message": "Missing return statements"})
    if user_dump.count("If(") < correct_dump.count("If("):
        issues.append({"message": "Missing conditional statements"})
    if user_dump.count("For(") < correct_dump.count("For("):
        issues.append({"message": "Missing loop structures"})

    # Always at least one generic issue if none of the above
    if not issues:
        issues.append({"message": "Code structure differs from expected solution"})

    score = max(10.0, sim - len(issues) * 10)

    return {
        "exact_match": False,
        "score": score,
        "feedback": {
            "message": f"AST similarity: {sim:.1f}%",
            "issues": [
                {
                    "line_number": 1,
                    "column": None,
                    "end_line_number": None,
                    "end_column": None,
                    "message": issue["message"]
                }
                for issue in issues
            ]
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
    """Parse user code, compare AST dumps, and return feedback."""
    try:
        user_dump = get_ast_dump(req.user_code)
    except HTTPException as he:
        log_error(req.question_id, req.user_code, he.detail)
        raise
    try:
        comparison = compare_ast(user_dump, req.correct_ast)
    except Exception as e:
        log_error(req.question_id, req.user_code, f"Internal error: {e}")
        raise HTTPException(status_code=500, detail="Internal error checking code")  from e
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
