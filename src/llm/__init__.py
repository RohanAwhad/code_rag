import os
import re

from . import model

SYS_PROMPT = '''
You are a language model, and your job is to help me build context for my prompt to a Coder Agent.

I will send you the entire code from the current file I am working on. 99% of the time, the last couple of lines will contain the things I want to do.

I want you to reason about what I want, what all code I currently have and then produce a search call to grab all the context required.

The way you should output is following:
1. First you will reason through what all I asked, and then you will generate 0 or more search queries.
2. Your search queries will have the following xml format:

<search_queries>
  <query_1>
    <query_text>some text here. try to keep it as similar as possible</query_text>
    <filename>possible filename or filepath like project/utils. Do not include any extension, because that might be a module or a file, which you do not know.</filename>
    <component_type>This should be one of 'class', 'function', 'param', or 'full_text' (full text returns the entire script)</component_type>
  </query_1>
  <query_2>
    [...]
  </query_2>
  [...]
</search_queries>

Instructions:
  - Be a good boy and reason and give me good search queries.
  - DO NOT try to answer my question.
  - First reason
  - then generate search queries
  - Query Text:
    - query is a search query.
    - it works using trigram search.
    - this should not be questions.
    - this should be text which closely resembles what you want, eg function name, class name, etc.
  - Filename:
    - DO NOT INCLUDE EXTENSIONS TO FILENAME
  - Component Type:
    - It should be one of "class", "function", "param" or "full_text"
    - Use "full_text" whenever you need to explore the entire file or module.
'''

qwen = model.OpenAIModel(
  base_url="http://localhost:11434/v1",
  api_key='ollama',
  model_name='qwen2.5-coder:7b',
)
gemini_flash = model.OpenAIModel(
  base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
  api_key=os.environ['GEMINI_API_KEY'],
  model_name='gemini-2.0-flash',
)


LLM = gemini_flash

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

def get_search_queries(user_prompt):
  global SYS_PROMPT

  modified_user_prompt = f'<user_prompt_for_coder>{user_prompt}</user_prompt_for_coder>\n\nGenerate search queries'
  messages = [
    model.Message(role='system', content=SYS_PROMPT),
    model.Message(role='user', content=modified_user_prompt),
  ]
  response = LLM.ask(messages)
  print(response)
  return parse_search_queries(response)

