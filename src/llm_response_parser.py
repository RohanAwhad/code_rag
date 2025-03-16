import re

def parse_search_queries(search_queries_text):
  """
  Parse the search queries from the XML-like format.

  Args:
      search_queries_text (str): XML-like string containing search queries

  Returns:
      list: List of dictionaries containing parsed query information
  """
  queries = []

  # Extract all query blocks
  query_blocks = re.findall(r'<query_\d+>(.*?)</query_\d+>', search_queries_text, re.DOTALL)

  for block in query_blocks:
    query = {}

    # Extract query text
    query_text_match = re.search(r'<query_text>(.*?)</query_text>', block, re.DOTALL)
    if query_text_match:
      query['query_text'] = query_text_match.group(1).strip()

    # Extract filename
    filename_match = re.search(r'<filename>(.*?)</filename>', block, re.DOTALL)
    if filename_match:
      query['filename'] = filename_match.group(1).strip()

    # Extract component type
    component_type_match = re.search(r'<component_type>(.*?)</component_type>', block, re.DOTALL)
    if component_type_match:
      query['component_type'] = component_type_match.group(1).strip()

    queries.append(query)

  return queries

