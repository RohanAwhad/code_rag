import claudette
import hashlib

from src import component_extractor, file_grabber, database, retriever, llm_response_parser

# EXAMPLE_PROJECT = "/Users/rohan/3_Resources/external_libs/gpt-researcher"
# EXAMPLE_PROJECT = "/Users/rohan/0_Inbox/testing_kokoro/kokoro-tts"
EXAMPLE_PROJECT = "/Users/rohan/1_Porn/PixQuery_django"

FILE_INDEX = {}

def remove_unchanged_files(file_list, FILE_INDEX):
  '''hash all files and check if they are same with previous ones, if yes, skip that file'''
  changed_files = []
  new_file_index = {}

  for file_path in file_list:
    try:
      with open(file_path, 'rb') as f:
        content = f.read()
        file_hash = hashlib.md5(content).hexdigest()

      new_file_index[file_path] = file_hash

      # Check if file is new or changed
      if file_path not in FILE_INDEX or FILE_INDEX[file_path] != file_hash:
        changed_files.append(file_path)
    except Exception as e:
      print(f"Error processing file {file_path}: {e}")
      # Include file in changed_files anyway to be safe
      changed_files.append(file_path)

  return changed_files, new_file_index


def call_retriever(query, component_type, filename, limit=2):
  print(query, component_type, filename)
  results = retriever.search_code(
    query=query,
    component_type=component_type,
    filename=filename,
    limit=limit,
  )
  print(results)
  ret = []

  for res in results:
    _tmp = '\n'
    _tmp += 'filename: ' + res['file_path'] + '\n'
    _tmp += 'component_name: ' + res['name'] + '\n'
    _tmp += 'code:\n'
    _tmp += res['code']
    _tmp += '\n' + '='*10
    ret.append(_tmp)

  return ''.join(ret)


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
    <filename>possible filename or filepath like project/utils</filename>
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
'''



def main(prompt):
  global FILE_INDEX

  python_files = file_grabber.grab_all_python_file(EXAMPLE_PROJECT)
  changed_python_files, FILE_INDEX = remove_unchanged_files(python_files, FILE_INDEX)
  if len(changed_python_files):
    df = component_extractor.extract(changed_python_files)
    database.push_to_db(df)

  llm = claudette.Chat(claudette.models[1], sp=SYS_PROMPT)
  op = llm(f'<user_prompt_for_coder>{prompt}</user_prompt_for_coder>\n\nGenerate search queries')
  response = op.content[0].text
  print(response)
  queries = llm_response_parser.parse_search_queries(response)

  print('Context')
  context = []
  for q in queries:
    context.append(call_retriever(
      query=q['query_text'],
      component_type=q['component_type'],
      filename=q['filename'],
      limit=2
    ))

  print('\n\n'.join(context))
  with open('tmp', 'w') as f: f.write('\n\n'.join(context))


if __name__ == '__main__':
  while True:
    main(prompt)
    input()


