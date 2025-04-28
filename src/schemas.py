from typing import List, Optional, Dict 
from pydantic import BaseModel


class ConstructAnswerItem(BaseModel):
    question_id: str
    correct_code: str

class ConstructedAnswer(BaseModel):
    code: str
    ast: str

class ConstructAnswersResponse(BaseModel):
    answers: Dict[str, ConstructAnswerItem]

class CheckAnswerRequest(BaseModel):
    question_id: str
    user_code: str
    correct_code: str 
    correct_ast: Optional[str] = None 

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
    exact_match: bool
    score: float
    feedback: Feedback
