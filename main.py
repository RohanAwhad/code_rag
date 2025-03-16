from src import component_extractor, grabber, database, retriever

# EXAMPLE_PROJECT = "/Users/rohan/3_Resources/external_libs/gpt-researcher"
# EXAMPLE_PROJECT = "/Users/rohan/0_Inbox/testing_kokoro/kokoro-tts"
EXAMPLE_PROJECT = "/Users/rohan/1_Porn/PixQuery_django"

python_files = grabber.grab_all_python_file(EXAMPLE_PROJECT)
df = component_extractor.extract(python_files)
database.push_to_db(df)

def call_retriever(query, component_type, filename, limit=10):
  results = retriever.search_code(
    query=query, 
    component_type=component_type,
    filename=filename,
    limit=limit,
  )

  for res in results:
    print()
    print('filename:', res['file_path'])
    print('component_name:', res['name'])
    print('code:')
    print(res['code'])
    print()
    print('='*10)



#
# call_retriever(
#   query='clip embedder get image embeddings',
#   component_type='function',
#   filename='chromadb_custom/embedder/clip_embedder.py',
#   limit=3,
# )


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

prompt = """
<user_prompt_for_coder>
from django.shortcuts import render
from django.db import connection
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from loguru import logger

from .utils import get_user_info, geocode_location, haversine
from chromadb_custom.utils import CHROMADB_CLIENT, ChromaDBWrapper
from imageprocessor.dropbox_utils import DropboxClient
from imageprocessor.models import ImageDetail, ImageTag, DropboxDir
from imageprocessor import tasks as imageprocessor_tasks

def up_view(request):
  return HttpResponse(status=200)

def search_home_view(request):
  if request.user.is_authenticated:
    user_info = get_user_info(request.user)
    dc = DropboxClient(request.user)
    dc.create_template()

    dir_url = dc.path_to_url(dc.upload_dir)
    if not DropboxDir.objects.filter(dir_url=dir_url, user=request.user).exists():
      DropboxDir(dir_url=dir_url, dir_path=dc.upload_dir, user=request.user, cursor=None).save()

    imageprocessor_tasks.sync_with_dropbox.delay()
    imageprocessor_tasks.poll_batch_results.apply_async(countdown=1800)  # 1800 seconds = 30 minutes

    return render(request, 'search/home.html', {'initials': user_info.initials})
  return render(request, 'home.html', {})

def search_result_view(request):
  if not request.user.is_authenticated:
    return render(request, 'home.html', {})

  query = request.GET.get('q', '')
  season = request.GET.get('season', '')
  location = request.GET.get('location', '')
  user_info = get_user_info(request.user)
  context = {
    'initials': user_info.initials,
    'query': query,
    'selected_season': season,
    'selected_location': location,
  }

  # Combined search
  search_results = combined_search(query, request.user, season, location)

  context['search_results'] = search_results
  return render(request, 'search/result.html', context)

def combined_search(query, user, season=None, location=None):
  # Get embedding for vector search
  from chromadb_custom.embedder import clip_embedder
  embedder = clip_embedder.Embedder()
  embedding = embedder.get_text_embeddings([query])[0]

  # Sanitize query for FTS
  sanitized_query = sanitize_fts_query(query)

  k = 60  # RRF constant

  params = {
    'query_text': sanitized_query,
    'query_embedding': embedding,
    'user_id': user.id,
    'season': season,
    'rrf_k': k,
    'full_text_weight': 1.0,
    'semantic_weight': 1.0
  }

  with connection.cursor() as cursor:
    cursor.execute('''
    WITH text_search AS (
      SELECT
        id.url,
        row_number() OVER (
          ORDER BY ts_rank_cd(it.title_caption_tags_fts_vector, websearch_to_tsquery(%(query_text)s)) DESC
        ) AS rank_ix
      FROM imageprocessor_imagetag it
      JOIN imageprocessor_imagedetail id ON it.img_id = id.url
      WHERE it.title_caption_tags_fts_vector @@ websearch_to_tsquery(%(query_text)s)
      AND id.user_id = %(user_id)s
      AND COALESCE(id.season = COALESCE(%(season)s, id.season), TRUE)
      ORDER BY rank_ix
      LIMIT 60
    ),
    vector_search AS (
      SELECT
        ie.image_id AS url,
        row_number() OVER (
          ORDER BY ie.embedding_vector <=> %(query_embedding)s::vector
        ) AS rank_ix
      FROM image_embeddings ie
      JOIN imageprocessor_imagedetail id ON ie.image_id = id.url
      WHERE id.user_id = %(user_id)s
      AND COALESCE(id.season = COALESCE(%(season)s, id.season), TRUE)
      ORDER BY rank_ix
      LIMIT 60
    )
    SELECT
      id.url,
      id.thumbnail_url,
      it.title,
      it.tags,
      id.coordinates
    FROM text_search
      FULL OUTER JOIN vector_search ON text_search.url = vector_search.url
      JOIN imageprocessor_imagedetail id ON COALESCE(text_search.url, vector_search.url) = id.url
      LEFT JOIN imageprocessor_imagetag it ON id.url = it.img_id
    ORDER BY
      COALESCE(1.0 / (%(rrf_k)s + text_search.rank_ix), 0.0) * %(full_text_weight)s +
      COALESCE(1.0 / (%(rrf_k)s + vector_search.rank_ix), 0.0) * %(semantic_weight)s DESC
    LIMIT 100
    ''', params)

    results = cursor.fetchall()

  # Apply location filtering in Python
  if location:
    target_coords = geocode_location(location)
    if target_coords:
      target_lat, target_lng = target_coords
      radius_km = 50

      filtered_results = []
      for result in results:
        coords = result[4]
        if coords:
          try:
            img_lat, img_lng = coords
            distance = haversine(target_lat, target_lng, img_lat, img_lng)
            if distance <= radius_km:
              filtered_results.append(result)
          except (TypeError, ValueError):
            continue

      results = filtered_results

  # Format results
  search_results = []
  for url, thumbnail_url, title, tags, _ in results:
    search_results.append({
      'dropbox_url': url,
      'src': thumbnail_url,
      'title': title or '',
      'tag_string': tags or '',
    })

  return search_results



def sanitize_fts_query(query: str) -> str:
  allowed = set(['AND', 'OR', 'NOT', '"', '*'])
  terms = query.split()
  sanitized = []

  for term in terms:
    if term in allowed:
      sanitized.append(term)
    else:
      cleaned = ''.join(c for c in term if c.isalnum() or c in ['-', '_'])
      if cleaned:
        sanitized.append(f'"{cleaned}"')

  return ' '.join(sanitized)



@login_required
@require_POST
def add_dir_view(request):
    dir_url = request.POST.get('dropbox_url')

    try:
        dir_path = DropboxClient.url_to_path(dir_url)
        dir_obj, created = DropboxDir.objects.get_or_create(
            dir_url=dir_url,
            user=request.user,
            defaults={'dir_path': dir_path}
        )
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def update_tags(request):
  if not request.user.is_authenticated:
    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

  dropbox_url = request.POST.get('dropbox_url')
  tags = request.POST.get('tags', '')
  tags_list = [x for x in tags.split(',') if x]
  tags = ','.join(tags_list)

  try:
    img = ImageDetail.objects.get(url=dropbox_url)
    img_tag = ImageTag.objects.get(img=img)
    img_tag.tags = tags
    img_tag.save()
    DropboxClient(request.user).push_tags(tags_list, img.drive_path)
    return JsonResponse({'status': 'success'})
  except ImageDetail.DoesNotExist:
    return JsonResponse({'status': 'error', 'message': 'Image not found'}, status=404)
  except ImageTag.DoesNotExist:
    return JsonResponse({'status': 'error', 'message': 'Image tag not found'}, status=404)
  except Exception as e:
    return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


write me a function that will perform similar search but using an image. it should only search based on image embeddings, and nothing else. no filters.
</user_prompt_for_coder>

Generate search queries
"""


import claudette
llm = claudette.Chat(claudette.models[1], sp=SYS_PROMPT)
op = llm(prompt)
print()
print(op.content[0].text)
print()
