import ast
import os
from collections import defaultdict


def find_imports_in_file(filepath):
    """Parse a Python file and return a list of imported modules."""
    with open(filepath, "r", encoding="utf-8") as file:
        node = ast.parse(file.read(), filename=filepath)

    imports = []

    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for alias in n.names:
                imports.append(alias.name)
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                imports.append(n.module)

    return imports


def build_import_graph(directory):
    """Build an import graph from the directory structure."""
    graph = defaultdict(list)
    module_file_map = {}

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                filepath = os.path.join(root, file)
                module_name = os.path.splitext(filepath.replace(directory, "").replace(os.path.sep, "."))[0].strip(".")
                imported_modules = find_imports_in_file(filepath)
                for imported_module in imported_modules:
                    graph[module_name].append(imported_module)
                module_file_map[module_name] = filepath

    return graph, module_file_map


def detect_cycles(graph):
    """Detect cycles in the import graph using DFS."""
    def dfs(node, visited, stack):
        visited.add(node)
        stack.add(node)
        for neighbor in graph.get(node, []):  # Use .get to avoid KeyError
            if neighbor not in visited:
                cycle = dfs(neighbor, visited, stack)
                if cycle:
                    return cycle
            elif neighbor in stack:
                return list(stack) + [neighbor]  # Return the cycle as a list
        stack.remove(node)
        return None

    visited = set()
    for node in list(graph.keys()):
        if node not in visited:
            cycle = dfs(node, visited, set())
            if cycle:
                return cycle
    return None


def move_import_to_function(filepath, import_name):
    """Move an import statement inside a function in the file to break a circular dependency."""
    with open(filepath, "r", encoding="utf-8") as file:
        lines = file.readlines()

    new_lines = []
    import_moved = False

    for line in lines:
        if not import_moved and (f"import {import_name}" in line or f"from {import_name}" in line):
            # Move this import into the first function or method
            import_moved = True
            for i, l in enumerate(lines):
                print(line, end="")
                if l.strip().startswith("def ") or l.strip().startswith("class "):
                    indent = ' ' * (len(l) - len(l.lstrip()))
                    new_lines.append(f"{indent}{line.strip()}\n")
                    break
        else:
            new_lines.append(line)

    with open(filepath, "w", encoding="utf-8") as file:
        file.writelines(new_lines)


def fix_circular_imports(directory):
    """Detect and attempt to fix circular imports in the given directory."""
    graph, module_file_map = build_import_graph(directory)
    cycle = detect_cycles(graph)

    if cycle:
        print("Circular import detected between the following modules:")
        for node in cycle:
            print(f"  {node}")
        print("Attempting to fix the circular import...")

        # Attempt to break the cycle by moving imports inside functions
        for module in cycle:
            filepath = module_file_map[module]
            for neighbor in graph[module]:
                if neighbor in cycle:
                    print(f"  Moving import of {neighbor} in {module}")
                    move_import_to_function(filepath, neighbor)

        print("Fix applied. Please review the changes manually.")

    else:
        print("No circular imports detected.")


# Example usage:
directory_path = "."  # Replace with the path to your project root
fix_circular_imports(directory_path)
