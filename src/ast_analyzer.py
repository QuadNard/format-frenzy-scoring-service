# src/ast_analyzer.py
import ast
from typing import List, Dict, Any

class NodeLocator(ast.NodeVisitor):
    """AST visitor that builds a mapping of node types to their locations."""
    
    def __init__(self, source_code: str):
        self.source_code = source_code.split('\n')
        self.node_locations = {}
        self.current_node_type = None
    
    def generic_visit(self, node):
        """Track node locations as we visit them."""
        if hasattr(node, 'lineno'):
            node_type = type(node).__name__
            if node_type not in self.node_locations:
                self.node_locations[node_type] = []
            
            end_lineno = getattr(node, 'end_lineno', node.lineno)
            end_col_offset = getattr(node, 'end_col_offset', len(self.source_code[node.lineno-1]) if node.lineno <= len(self.source_code) else 0)
            
            self.node_locations[node_type].append({
                'lineno': node.lineno,
                'col_offset': node.col_offset,
                'end_lineno': end_lineno,
                'end_col_offset': end_col_offset
            })
        
        ast.NodeVisitor.generic_visit(self, node)

def find_missing_nodes(user_code: str, correct_code: str) -> List[Dict[str, Any]]:
    """Find nodes present in correct_code but missing in user_code."""
    user_tree = ast.parse(user_code)
    correct_tree = ast.parse(correct_code)
    
    # Get node types and counts from both trees
    user_node_types = {}
    correct_node_types = {}
    
    for node in ast.walk(user_tree):
        node_type = type(node).__name__
        user_node_types[node_type] = user_node_types.get(node_type, 0) + 1
    
    for node in ast.walk(correct_tree):
        node_type = type(node).__name__
        correct_node_types[node_type] = correct_node_types.get(node_type, 0) + 1
    
    # Find location information for nodes in the correct code
    locator = NodeLocator(correct_code)
    locator.visit(correct_tree)
    node_locations = locator.node_locations
    
    # Identify missing nodes
    issues = []
    for node_type, count in correct_node_types.items():
        user_count = user_node_types.get(node_type, 0)
        if user_count < count:
            missing_count = count - user_count
            message = f"Missing {missing_count} {node_type} node(s)"
            
            # Add location of first missing node if available
            if node_type in node_locations and len(node_locations[node_type]) >= user_count + 1:
                location = node_locations[node_type][user_count]
                issues.append({
                    "line_number": location['lineno'],
                    "column": location['col_offset'],
                    "end_line_number": location['end_lineno'],
                    "end_column": location['end_col_offset'],
                    "message": message
                })
            else:
                # Fallback if location can't be determined
                issues.append({
                    "line_number": 1, 
                    "column": None,
                    "end_line_number": None,
                    "end_column": None,
                    "message": message
                })
    
    return issues