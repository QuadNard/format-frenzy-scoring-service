from typing import List, Optional
from pydantic import BaseModel


class QuestionSet(BaseModel):
    question_id: str
    correct_code: str

class ConstructAnswerItem(BaseModel):
    question_id: str
    ast_dump: str

class ConstructAnswersResponse(BaseModel):
    answers: List[ConstructAnswerItem]

class CheckAnswerRequest(BaseModel):
    question_id: str
    correct_code: str
    user_code: str
    correct_ast: str    # AST dump as a string

class CodeIssue(BaseModel):
    line_number: int
    column: Optional[int] = None
    end_line_number: Optional[int] = None
    end_column: Optional[int] = None
    message: str

class Feedback(BaseModel):
    message: str
    issues: List[CodeIssue] = []

class ScoreResponse(BaseModel):
    correct: bool
    points: int
    feedback: Optional[List[str]] = None
    exact_match: bool
    score: float
    feedback: Feedback
