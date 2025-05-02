import difflib
import ast
from typing import List, Dict, Any
import os
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

from src.scoring import compare_ast
from src.ast_analyzer import find_missing_nodes
from src.server.cruds import crud_router_v1
from src.utils.error_logger import error_logger, log_error
from dotenv import load_dotenv


load_dotenv() 


env = os.getenv("ENV", "production")
origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "")
           .split(",") if origin.strip()]



# TODO: Move this to utils/ast_utils.py
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

# Define lifespan handler first
@asynccontextmanager
async def lifespan_handler(_: FastAPI):
    # Startup code (runs before first request)
    yield
    # Shutdown code (runs after server stops)
    error_logger.shutdown()

# Instantiate FastAPI with the lifespan handler
app = FastAPI(lifespan=lifespan_handler)

# Simple in-memory cache for AST dumps
# TODO: Replace with Redis or similar in production
ast_cache = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(crud_router_v1, prefix="/v1")

@app.get("/")
async def root():
    return {"message": "OK"}

# TODO: Move this to a separate route file later
@app.post("/construct-answers", response_model=Dict[str, Any])
async def construct_answers(items: List[ConstructAnswerItem]):
    """
    Process and return AST dumps for correct answers.
    Can be moved to a separate route file when it grows.
    """
    result = {}
    for item in items:
        # Check if we have this code in cache
        cache_key = f"correct_{item.question_id}"
        if cache_key in ast_cache:
            result[item.question_id] = ast_cache[cache_key]
        else:
            dump = get_ast_dump(item.correct_code)
            ast_cache[cache_key] = dump
            result[item.question_id] = dump
   
    return result

@app.post("/check-answer", response_model=ScoreResponse)
async def check_answer(req: CheckAnswerRequest):
    """Compare user code against correct AST and return feedback."""
    # Generate cache key for this submission
    cache_key = f"user_{req.question_id}_{hash(req.user_code)}"
    
    # Check if we have results cached
    if cache_key in ast_cache:
        return ast_cache[cache_key]
    
    try:
        # Use the supplied correct_code for advanced comparison
        # If you need to use correct_ast for legacy compatibility, it's available as req.correct_ast
        result = compare_ast(req.user_code, req.correct_code)
        
        # If we need additional analysis for more specific feedback
        try:
            missing_nodes = find_missing_nodes(req.user_code, req.correct_code)
            if missing_nodes and not result["exact_match"]:
                # Add missing nodes to our issues
                result["feedback"]["issues"].extend(missing_nodes)
        except ImportError as node_error:
            # If node analysis fails, just log it but continue with the basic comparison
            log_error(req.question_id, req.user_code, f"Node analysis error: {node_error}")
    
    except SyntaxError as e:
        log_error(req.question_id, req.user_code, f"Syntax error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Syntax error on line {e.lineno}, col {e.offset}: {e.msg}"
        ) from e
    except Exception as e:
        log_error(req.question_id, req.user_code, f"Internal error: {e}")
        # More specific error message
        raise HTTPException(
            status_code=500, 
            detail="Failed during AST structure comparison"
        ) from e
    
    response = ScoreResponse(
        exact_match=result["exact_match"],
        score=result["score"],
        feedback=Feedback(
            message=result["feedback"]["message"],
            issues=[CodeIssue(**i) for i in result["feedback"]["issues"]]
        )
    )
    
    # Cache the result
    ast_cache[cache_key] = response
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)