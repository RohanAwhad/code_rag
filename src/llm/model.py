from anthropic import Anthropic
from openai import OpenAI
from pydantic import BaseModel

class Message:
  def __init__(self, role: str, content: str | dict):
    if role not in ('system', 'user', 'assistant'):
      raise ValueError(f'role expected to be one of system, user and assistant. got {role}')
    self.role = role

    if role == 'system' and not isinstance(content, str):
      raise TypeError(f'for system prompt, content has to be str. got {type(content)}')

    if isinstance(content, dict):
      raise NotImplementedError('dict as content not yet implemented')
    elif isinstance(content, str):
      self.content = content
    else:
      raise TypeError(f'content should be str or dict, but got {type(content)}')

  def to_dict(self) -> dict:
    return dict(role=self.role, content=self.content)


class OpenAIModel(BaseModel):
  base_url: str
  api_key: str
  model_name: str
  temperature: float = 0.7
  max_tokens: int = 1024

  def ask(self, messages: list[Message]):
    client = OpenAI(api_key=self.api_key, base_url=self.base_url)
    response = client.chat.completions.create(
      model=self.model_name,
      messages=[x.to_dict() for x in messages],
      temperature=self.temperature,
      max_tokens=self.max_tokens,
    )
    return response.choices[0].message.content


class AnthropicModel:
  api_key: str
  model_name: str

  def __init__(self, api_key: str, model_name: str):
    self.api_key = api_key
    self.model_name = model_name
    self.client = Anthropic(api_key=self.api_key)

  def ask(self, messages: list[Message]):
    sys_prompt = self._get_sys_prompt(messages)
    if sys_prompt is not None: messages = messages[1:]

    response = self.client.messages.create(
      model="claude-3-5-sonnet-20240620",
      max_tokens=300,
      temperature=0.7,
      messages=[x.to_dict() for x in messages],
      system=sys_prompt,
      stream=False,
    )
    return response.content[0].text

  def _get_sys_prompt(self, messages: list[Message]) -> str | None:
    return messages[0].content if messages[0].role == 'system' else None




def ask_llm(model: OpenAIModel | AnthropicModel, messages: list[Message]):
  client = OpenAI(api_key=model.api_key, base_url=model.base_url)
  response = client.chat.completions.create(
    model=model.model_name,
    messages=[dict(x) for x in messages],
    temperature=model.temperature,
    max_tokens=model.max_tokens,
  )
  return response.choices[0].message.content

