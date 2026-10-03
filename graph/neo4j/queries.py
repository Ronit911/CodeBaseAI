"""
Cypher queries used for graph traversal during retrieval (Phase 5+).
"""

# Find all functions a given function calls
FUNCTION_CALLS_QUERY = """
MATCH (fn:Function {name: $name})-[:CALLS]->(callee:Function)
RETURN callee.name AS name, callee.file AS file
"""

# Find all functions inside a file
FILE_CONTENTS_QUERY = """
MATCH (f:File {path: $path})-[:CONTAINS]->(fn)
RETURN fn.name AS name, labels(fn)[0] AS type, fn.start_line AS start_line
"""

# Find files that import a given module
IMPORTS_QUERY = """
MATCH (f:File)-[:IMPORTS]->(m:Module {name: $module})
RETURN f.path AS file
"""

# Find callers of a given function
CALLERS_QUERY = """
MATCH (caller:Function)-[:CALLS]->(fn:Function {name: $name})
RETURN caller.name AS name, caller.file AS file
"""
