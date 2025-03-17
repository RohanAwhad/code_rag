import hashlib

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


def deduplicate(results):
  ret = []
  visited = set()  # tuple(file_path, component_type, component_name)
  for res in results:
    state = (res['file_path'], res['component_type'], res['name'])
    if state in visited: continue
    visited.add(state)
    ret.append(res)
  return ret


def format_results(results):
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


