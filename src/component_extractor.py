import ast
import os
import pandas as pd

def extract_components(file_path):
    # Read the file content
    with open(file_path, 'r') as f:
        source = f.read()
    
    # Parse the source code into an AST
    tree = ast.parse(source)
    
    # Initialize result dictionaries
    functions = {}
    classes = {}
    global_params = {}
    expressions = []
    imports = []
    
    # Set parent references for all nodes
    def set_parents(node, parent=None):
        node.parent = parent
        for child in ast.iter_child_nodes(node):
            set_parents(child, node)
    set_parents(tree)
    
    # Extract components
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):# and isinstance(node.parent, ast.Module):
            # Only include functions whose parent is the module (top-level)
            start_line = node.lineno - 1
            end_line = node.end_lineno
            func_text = '\n'.join(source.splitlines()[start_line:end_line])
            functions[node.name] = func_text
            
        elif isinstance(node, ast.ClassDef):
            start_line = node.lineno - 1
            end_line = node.end_lineno
            class_text = '\n'.join(source.splitlines()[start_line:end_line])
            classes[node.name] = class_text
            
        elif isinstance(node, ast.Assign) and isinstance(node.parent, ast.Module):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    start_line = node.lineno - 1
                    end_line = node.end_lineno
                    param_text = '\n'.join(source.splitlines()[start_line:end_line]).strip()
                    global_params[target.id] = param_text
                    
        elif isinstance(node, ast.Expr) and isinstance(node.parent, ast.Module):
            start_line = node.lineno - 1
            end_line = node.end_lineno
            expr_text = '\n'.join(source.splitlines()[start_line: end_line]).strip()
            expressions.append(expr_text)

        # New condition for imports
        # elif isinstance(node, (ast.Import, ast.ImportFrom)) and isinstance(node.parent, ast.Module):
        #     prefix = ''
        #     if isinstance(node, ast.ImportFrom):
        #         prefix += '.'*node.level + node.module +'.'
        #
        #     for n in node.names: imports.append(prefix + n.name) 

    return functions, classes, global_params, expressions, imports


def to_df(components):
  # Flatten all the components in a pandas df
  rows = []

  for file_path, file_components in components.items():
    # add full text
    rows.append({
      'file_path': file_path,
      'component_type': 'full_text',
      'name': os.path.basename(file_path),
      'code': file_components['full_text'],
    })

    # Add functions
    for func_name, func_data in file_components['functions'].items():
      rows.append({
        'file_path': file_path,
        'component_type': 'function',
        'name': func_name,
        'code': func_data,
      })
      
    # Add classes
    for class_name, class_data in file_components['classes'].items():
      rows.append({
        'file_path': file_path,
        'component_type': 'class',
        'name': class_name,
        'code': class_data,
      })

    # Add params
    for param_name, param_data in file_components['params'].items():
      rows.append({
        'file_path': file_path,
        'component_type': 'param',
        'name': param_name,
        'code': param_data,
      })
    
  # Create DataFrame
  df = pd.DataFrame(rows)

  # Display basic stats
  print(f"Total components: {len(df)}")
  print(f"Components by type: {df['component_type'].value_counts()}")
  print(df)
  return df



def extract(files: list[str]):
    # extract components
    components = {}
    for file in files:
      with open(file, 'r') as f: full_text = f.read().strip()
      funcs, classes, params, _, _ = extract_components(file)
      components[file] = {
        'functions': funcs,
        'classes': classes,
        'params': params,
        'full_text': full_text,
      }

    return to_df(components)


