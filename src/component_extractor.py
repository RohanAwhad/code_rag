import aiofiles
import asyncio
import os
import pandas as pd
import tree_sitter_python as tspython

from loguru import logger
from tree_sitter import Language, Parser


QUERIES = {
    'function': "(module (function_definition name: (identifier) @function_name) @function_def)",
    'class': "(module (class_definition name: (identifier) @class_name) @class_def)",
    'param': "(module (expression_statement (assignment left: (identifier) @global_param (_) @initial_value)))",
}

def extract_components(source: str):
    
    # Parse the source code into an AST
    lang = Language(tspython.language())
    parser = Parser(lang)
    tree = parser.parse(bytes(source, "utf8"))
    
    # Initialize result dictionaries
    functions = {}
    classes = {}
    global_params = {}

    # Extract functions
    query = lang.query(QUERIES['function'])
    captures = query.captures(tree.root_node)
    if captures:
        for def_node, name_node in zip(captures['function_def'], captures['function_name']):
            functions[name_node.text.decode('utf8')] = def_node.text.decode('utf8')

    # Extract classes
    query = lang.query(QUERIES['class'])
    captures = query.captures(tree.root_node)
    if captures:
        for def_node, name_node in zip(captures['class_def'], captures['class_name']):
            classes[name_node.text.decode('utf8')] = def_node.text.decode('utf8')

    # Extract global parameters
    query = lang.query(QUERIES['param'])
    captures = query.captures(tree.root_node)
    if captures:
        for def_node, name_node in zip(captures['initial_value'], captures['global_param']):
            global_params[name_node.text.decode('utf8')] = def_node.text.decode('utf8')
    return functions, classes, global_params


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


async def read_file(file):
  """Reads a file asynchronously and returns its contents."""
  async with aiofiles.open(file, 'r') as f:
    return await f.read()

async def process_file(file):
  try:
    full_text = await read_file(file)
    funcs, classes, params = extract_components(full_text)
    components = {
      'functions': funcs,
      'classes': classes,
      'params': params,
      'full_text': full_text,
    }
    return components
  except Exception:
    logger.exception(f'extraction failed for: {file}')
  return None

async def extract(files: list[str]):
  # extract components
  components = {}
  BATCH_SIZE = 512
  for i in range(0, len(files), BATCH_SIZE):
    batch = files[i:i + BATCH_SIZE]
    tasks = [process_file(file) for file in batch]
    results = await asyncio.gather(*tasks)
    for file, result in zip(batch, results):
      if result is not None:
        components[file] = result

  return to_df(components) if len(components) else None

if __name__ == "__main__":
    example_codes = {
        'python': """
b = 1
def extract(files: list[str]):
    # extract components
    components = {}
    for file in files:
      try:
          with open(file, 'r') as f: full_text = f.read().strip()
          funcs, classes, params = extract_components(full_text)
          components[file] = {
            'functions': funcs,
            'classes': classes,
            'params': params,
            'full_text': full_text,
          }
      except Exception as e:
        logger.exception(f'extraction failed for: {file}')
    return to_df(components) if len(components) else None

a = 1

class Test:
    def __init__(self):
        self.a = 1
    def test(self):
        pass

    class Config:
        model_config = "test"
        """
    }
    # example usage
    for lang in ['python']:
        code = example_codes.get(lang, "")
        if code:
            functions, classes, params = extract_components(code)
            print(f"{lang} params: {len(params)}")
            for param_name, param_val in params.items():
                print(f"  - {param_name}: {param_val}")
            print(f"{lang} functions: {len(functions)}")
            for func_name, func_val in functions.items():
                print(f"  - {func_name}: {func_val}")
            print(f"{lang} classes: {len(classes)}")
            for class_name, class_val in classes.items():
                print(f"  - {class_name}: {class_val}")



