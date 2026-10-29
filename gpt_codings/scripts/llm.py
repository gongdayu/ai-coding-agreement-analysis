"""API adapter and response parser; new guards do not prove historical runs."""
import ast
import json
import re

def new_message_object(role, content):
    return {"role": role, "content": content}

def extract_string(text):
    """Read JSON first, retaining old Python-literal compatibility."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Model response must be nonempty text")
    value = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", value, re.I | re.S)
    if fenced: value = fenced.group(1).strip()
    try:
        result = json.loads(value)
    except json.JSONDecodeError:
        try: result = ast.literal_eval(value)
        except (ValueError, SyntaxError) as exc:
            raise ValueError("Response is neither JSON nor a Python dictionary literal") from exc
    if not isinstance(result, dict) or not result:
        raise ValueError("Response must be a nonempty dictionary")
    return result

def run_completion_gpt(messages, model, temperature=0, response_format=None):
    from openai import OpenAI
    client = OpenAI(max_retries=0)
    if response_format:
        response = client.beta.chat.completions.parse(model=model, messages=messages, temperature=temperature, response_format=response_format)
    else:
        response = client.chat.completions.create(model=model, messages=messages, temperature=temperature)
    choice = response.choices[0]
    return {"response": choice.message.content, "returned_model": response.model,
            "response_id": response.id, "finish_reason": choice.finish_reason,
            "usage": response.usage.model_dump() if response.usage else None}
