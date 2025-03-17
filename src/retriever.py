from src.database import get_connection

def get_definition(
  filename: str,
  function_names: list[str] = None,
  class_names: list[str] = None,
  param_names: list[str] = None,
) -> str:
  """
  Retrieve definitions from the code database based on specified criteria.
  """
  conn = get_connection()
  cursor = conn.cursor()
  
  results = []
  
  # Base of the file path query
  file_condition = f"file_path LIKE '%{filename}%'"
  
  # Query for functions if requested
  if function_names:
    placeholders = ','.join(['%s' for _ in function_names])
    query = f"""
    SELECT name, code FROM function_indices
    WHERE {file_condition} AND name IN ({placeholders})
    """
    cursor.execute(query, function_names)
    for name, code in cursor.fetchall():
      results.append(f"Function: {name}\n{code}\n")
  
  # Query for classes if requested
  if class_names:
    placeholders = ','.join(['%s' for _ in class_names])
    query = f"""
    SELECT name, code FROM class_indices
    WHERE {file_condition} AND name IN ({placeholders})
    """
    cursor.execute(query, class_names)
    for name, code in cursor.fetchall():
      results.append(f"Class: {name}\n{code}\n")
  
  # Query for parameters if requested
  if param_names:
    placeholders = ','.join(['%s' for _ in param_names])
    query = f"""
    SELECT name, code FROM param_indices
    WHERE {file_condition} AND name IN ({placeholders})
    """
    cursor.execute(query, param_names)
    for name, code in cursor.fetchall():
      results.append(f"Parameter: {name}\n{code}\n")
  
  conn.close()
  
  if not results:
    return f"No definitions found in {filename} matching the specified criteria."
  
  return "\n".join(results)

def search_code(
  query: str,
  project_path: str,
  component_type: str = None,
  filename: str = None,
  limit: int = 10
) -> list[dict]:
  """
  Search code components using trigram similarity.
  """
  conn = get_connection()
  cursor = conn.cursor()
  
  # Build the query conditions
  conditions = []
  params = {}
  order_clause = ''

  params['project_path'] = project_path
  conditions.append('project_path = %(project_path)s')

  if query:
    params['query'] = query
    order_clause = 'ORDER BY similarity(code, %(query)s) DESC'
  
  if component_type:
    conditions.append("component_type = %(component_type)s")
    params['component_type'] = component_type
  
  if filename:
    conditions.append("file_path LIKE %(filename)s")
    params['filename'] = f'%{filename}%'
  
  # Add limit parameter
  params['limit'] = limit
  
  # Construct the query with named parameters
  where_clause = " AND ".join(conditions) if conditions else "TRUE"
  sql_query = f"""
  SELECT file_path, component_type, name, code 
  FROM components
  WHERE {where_clause}
  {order_clause}
  LIMIT %(limit)s
  """
  cursor.execute(sql_query, params)

  results = []
  for file_path, component_type, name, code in cursor.fetchall():
    results.append({
      'file_path': file_path,
      'component_type': component_type,
      'name': name,
      'code': code
    })
  
  conn.close()
  return results

