import os


# list all python files
def grab_all_python_file(project_path):
  python_files = []
  for root, dirs, files in os.walk(project_path):
    if '.venv' in root: continue  # skip venv for now
    for file in files:
      if file.endswith('.py'):
        python_files.append(os.path.join(root, file))
  return python_files
