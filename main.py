from loguru import logger

from src import (
  component_extractor,
  file_grabber,
  database,
  retriever,
  llm,
  utils,
)


def main(user_prompt, project_path):
  python_files = file_grabber.grab_all_python_file(project_path)
  changed_python_files, SESSION_DATA['FILE_INDEX'] = utils.remove_unchanged_files(python_files, SESSION_DATA['FILE_INDEX'])
  if len(changed_python_files):
    df = component_extractor.extract(changed_python_files)
    database.push_to_db(df, project_path)

  queries = llm.get_search_queries(user_prompt)
  all_results = []
  for q in queries:
    results = retriever.search_code(
      query=q['query_text'],
      component_type=q['component_type'],
      filename=q['filename'],
      limit=2
    )
    all_results.extend(results)
  all_results = utils.deduplicate(all_results)
  context = utils.format_results(all_results)
  return context

# ===
# FastAPI
# ===
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import uvicorn
import argparse

app = FastAPI()
SESSION_DATA = {'FILE_INDEX': {}}

class PromptRequest(BaseModel):
    prompt: str

@app.post("/", response_class=PlainTextResponse)
async def process_prompt(request: PromptRequest):
    try:
      context = main(request.prompt, SESSION_DATA['project_path'])
      return context
    except Exception as e:
      logger.exception('internal server err')
      return ''

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def start_server(project_path: str, host: str = "0.0.0.0", port: int = 8000):
    SESSION_DATA['project_path'] = project_path
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code context server")
    parser.add_argument("project_path", type=str, help="Path to the project to analyze")
    parser.add_argument("--host", type=str, default="localhost", help="Host to run the server on")
    parser.add_argument("--port", type=int, default=9999, help="Port to run the server on")
    
    args = parser.parse_args()
    
    print(f"Starting server for project: {args.project_path}")
    print(f"Server running at http://{args.host}:{args.port}")
    
    start_server(args.project_path, args.host, args.port)

