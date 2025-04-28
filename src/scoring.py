import ast
import difflib
import re
from typing import List, Dict, Any, Tuple
from collections import Counter

# Scoring system constants based on the rubric
EXACT_MATCH_SCORE = 27.0
HIGH_SIMILARITY_MULTIPLIER = 4
HIGH_SIMILARITY_DIVISOR = 8
HIGH_SIMILARITY_THRESHOLD = 0.85
INTERPRETABLE_MULTIPLIER = 1
INTERPRETABLE_DIVISOR = 7
INTERPRETABLE_THRESHOLD = 0.3
VALID_WRONG_INTENT_SCORE = 0
GARBAGE_MULTIPLIER = -1
GARBAGE_DIVISOR = 7

# Enhanced code structure indicators
CODE_STRUCTURE_KEYWORDS = ['def', 'return', 'for', 'if', 'while', 'class', 'import', 'with', 'try']
SYNTAX_PATTERNS = {
    'function': r'def\s+\w+\s*\(',
    'class': r'class\s+\w+',
    'import': r'(import|from)\s+[\w\.]+',
    'loop': r'(for|while)\s+.+:',
    'condition': r'if\s+.+:',
}

class ASTFeatureExtractor:
    """Extract meaningful features from AST for better similarity comparison."""
    
    @staticmethod
    def extract_features(tree: ast.AST) -> Dict[str, int]:
        """Extract key features from an AST."""
        features = Counter()
        
        # Count node types
        for node in ast.walk(tree):
            features[node.__class__.__name__] += 1
            
            # Count function names
            if isinstance(node, ast.FunctionDef):
                features[f"func:{node.name}"] += 1
                
            # Count class names
            elif isinstance(node, ast.ClassDef):
                features[f"class:{node.name}"] += 1
                
            # Count import names
            elif isinstance(node, ast.Import):
                for name in node.names:
                    features[f"import:{name.name}"] += 1
            elif isinstance(node, ast.ImportFrom):
                features[f"import_from:{node.module}"] += 1
                
            # Count call names
            elif isinstance(node, ast.Call) and hasattr(node.func, 'id'):
                features[f"call:{node.func.id}"] += 1
        
        return dict(features)
    
    @staticmethod
    def similarity_score(features1: Dict[str, int], features2: Dict[str, int]) -> float:
        """Calculate similarity score between two feature sets."""
        all_keys = set(features1.keys()) | set(features2.keys())
        if not all_keys:
            return 1.0
            
        differences = 0
        for key in all_keys:
            val1 = features1.get(key, 0)
            val2 = features2.get(key, 0)
            differences += abs(val1 - val2)
            
        # Normalize by total feature count
        total_features = sum(features1.values()) + sum(features2.values())
        if total_features == 0:
            return 1.0
            
        similarity = 1.0 - (differences / (total_features + len(all_keys)))
        return max(0.0, min(1.0, similarity))

def analyze_syntax_patterns(code: str) -> Dict[str, bool]:
    """
    Analyze code for syntax patterns even when it contains errors.
    Returns a dictionary of patterns found.
    """
    patterns = {}
    for name, pattern in SYNTAX_PATTERNS.items():
        patterns[name] = bool(re.search(pattern, code))
    return patterns

def estimate_code_quality(code: str) -> Tuple[float, List[str]]:
    """
    Estimate code quality for code with syntax errors.
    Returns a quality score between 0.0 and 1.0 and a list of issues.
    """
    patterns = analyze_syntax_patterns(code)
    issues = []
    
    # Count pattern matches
    pattern_score = sum(1 for p in patterns.values() if p) / len(patterns)
    
    # Check for basic syntax elements
    if not any(kw in code for kw in CODE_STRUCTURE_KEYWORDS):
        issues.append("No recognizable code structures found")
        pattern_score *= 0.5
    
    # Check for basic syntax errors that indicate some attempt was made
    if code.count('(') != code.count(')'):
        issues.append("Unbalanced parentheses")
    if code.count('{') != code.count('}'):
        issues.append("Unbalanced braces")
    if code.count('[') != code.count(']'):
        issues.append("Unbalanced brackets")
    
    # Check for indentation patterns
    lines = code.split('\n')
    has_indentation = any(line.startswith(' ') or line.startswith('\t') for line in lines)
    if not has_indentation and any(line.rstrip().endswith(':') for line in lines):
        issues.append("Missing indentation after blocks")
        pattern_score *= 0.8
    
    # Look for common Python syntax errors
    if re.search(r'[^=!<>]=[^=]', code) and not re.search(r'def\s+\w+\s*\([^)]*=', code):
        # Has assignment but not in function defaults
        pattern_score = max(pattern_score, 0.3)  # At least some attempt at logic
    
    # Calculate final quality score
    quality_score = pattern_score * (0.8 if issues else 1.0)
    
    return quality_score, issues

def compare_ast(user_code: str, correct_code: str) -> Dict[str, Any]:
    """
    Apply point-based rubric to AST comparison:
    - Exact Match: +27 points
    - Slight Syntax Error (High Similarity): +4 * (lines // 8)
    - Interpretable but Invalid Syntax: +1 * (lines // 7)
    - Valid but Wrong Intent: 0 points
    - Garbage: -1 * (lines // 7)
    """
    user_lines = user_code.strip().splitlines()
    correct_lines = correct_code.strip().splitlines()
    line_count = max(1, len(user_lines))  # Avoid division by 0
    
    try:
        user_ast = ast.parse(user_code)
        correct_ast = ast.parse(correct_code)
        
        # Extract features for more nuanced comparison
        user_features = ASTFeatureExtractor.extract_features(user_ast)
        correct_features = ASTFeatureExtractor.extract_features(correct_ast)
        
        # Calculate feature-based similarity
        feature_sim = ASTFeatureExtractor.similarity_score(user_features, correct_features)
        
        # Standard AST comparison
        user_dump = ast.dump(user_ast, include_attributes=False)
        correct_dump = ast.dump(correct_ast, include_attributes=False)
        
        # Check for exact match (✅ Exact Match)
        if user_dump == correct_dump:
            return score_response(True, EXACT_MATCH_SCORE, [])
            
        # Calculate text-based similarity
        text_sim = difflib.SequenceMatcher(None, user_dump, correct_dump).ratio()
        
        # Use a weighted combination of both similarity metrics
        sim_ratio = 0.7 * feature_sim + 0.3 * text_sim
        
        # Identify specific structural issues
        issues = []
        if user_features.get('Return', 0) < correct_features.get('Return', 0):
            issues.append("Missing return statements")
        if user_features.get('If', 0) < correct_features.get('If', 0):
            issues.append("Missing conditional statements")
        if user_features.get('For', 0) < correct_features.get('For', 0):
            issues.append("Missing loop structures")
        
        # Special case: check for import patterns
        correct_imports = {k: v for k, v in correct_features.items() if k.startswith('import:')}
        user_imports = {k: v for k, v in user_features.items() if k.startswith('import:')}
        if correct_imports and not user_imports:
            issues.append("Missing required imports")
        
        # Apply scoring logic based on similarity
        if sim_ratio > HIGH_SIMILARITY_THRESHOLD:
            # 🔶 Slight Syntax Error (High Similarity)
            score = HIGH_SIMILARITY_MULTIPLIER * (line_count // HIGH_SIMILARITY_DIVISOR)
        elif sim_ratio > INTERPRETABLE_THRESHOLD:
            # 🔸 Interpretable but different from expected
            score = INTERPRETABLE_MULTIPLIER * (line_count // INTERPRETABLE_DIVISOR)
        else:
            # ⚠ Valid but Wrong Intent
            score = VALID_WRONG_INTENT_SCORE
        
        return score_response(False, score, issues or ["Structure differs from expected solution"])
        
    except SyntaxError:
        # Enhanced analysis for code with syntax errors
        quality_score, syntax_issues = estimate_code_quality(user_code)
        
        if quality_score > HIGH_SIMILARITY_THRESHOLD:
            # High quality code with minor syntax errors
            score = HIGH_SIMILARITY_MULTIPLIER * (line_count // HIGH_SIMILARITY_DIVISOR)
            return score_response(False, score, ["Minor syntax errors"] + syntax_issues)
        elif quality_score > INTERPRETABLE_THRESHOLD:
            # Code appears to have structure but invalid syntax (Interpretable)
            score = INTERPRETABLE_MULTIPLIER * (line_count // INTERPRETABLE_DIVISOR)
            return score_response(False, score, ["Code structure somewhat interpretable, but syntax is invalid"] + syntax_issues)
        else:
            # Code appears to be nonsensical (Garbage)
            score = GARBAGE_MULTIPLIER * (line_count // GARBAGE_DIVISOR)
            return score_response(False, score, ["Code is nonsensical or unrecognizable"] + syntax_issues)

def score_response(exact: bool, score: float, messages: List[str]) -> Dict[str, Any]:
    """
    Generate a standardized response object with scoring information.
    
    Args:
        exact: Whether the solution is an exact match
        score: The numerical score assigned
        messages: List of feedback messages
        
    Returns:
        Dictionary with scoring details and feedback
    """
    return {
        "exact_match": exact,
        "score": score,
        "feedback": {
            "message": "Perfect match!" if exact else "Review your code structure.",
            "issues": [
                {
                    "line_number": 1,
                    "column": None,
                    "end_line_number": None,
                    "end_column": None,
                    "message": msg
                }
                for msg in messages
            ]
        }
    }