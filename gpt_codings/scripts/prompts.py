"""Prompt templates and how each one is filled.

The templates live in ../prompts/*.txt and are the exact prompt strings used in
the original notebooks:
  prompt_1    Method 1, single step (analisys_prompt_1)
  prompt_1_1  Method 2, step 1: research goal and findings (analisys_prompt_1_1)
  prompt_1_2  Method 2, step 2: categorise each finding (analisys_prompt_1_2)
  prompt_2    Review type and significance (analisys_prompt_2)
"""
import hashlib
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

PROMPT_NAMES = ["1", "1_1", "1_2", "2"]

# Placeholder in each template, and the input it is filled with.
PLACEHOLDERS = {
    "1": "{pdf_text}",
    "1_1": "{pdf_text}",
    "1_2": "{research_goal_and_finding_to_analyze}",
    "2": "{pdf_text}",
}


def load_template(name):
    with open(PROMPT_DIR / f"prompt_{name}.txt", encoding="utf-8", newline="") as f:
        return f.read()


def fill_prompt(template, name, value):
    """Return the prompt text sent to the model.

    `value` is the article text for prompts 1, 1_1 and 2, and the parsed result
    of prompt 1_1 (a dict) for prompt 1_2. As in the notebooks, it is inserted
    with str().
    """
    return template.replace(PLACEHOLDERS[name], str(value))


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
