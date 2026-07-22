# GPT Coding Notebooks

This folder contains the GPT coding notebooks used to generate model-coded data
from article PDFs.

## Notebooks

- `paper_scope_review_prompt_1_2_gpt4-1.ipynb`: GPT-4.1 Method 1 coding workflow.
- `paper_scope_review_prompt_1.1_1.2_2_gpt4-1.ipynb`: GPT-4.1 Method 2 coding workflow.
- `paper_scope_review_prompt_1.1_1.2_2_gpt5-4.ipynb`: GPT-5.4 Method 2 coding workflow.

## Inputs

Place article PDFs locally in:

```text
data/pdf_to_review/
```

The notebooks extract PDF text to `data/pdf_text.json` and write coding outputs
to local JSON/CSV files. These generated files are not included in the public
repository.

## API Key

Set the OpenAI API key in the environment before running:

```bash
export OPENAI_API_KEY="your-api-key"
```

Do not hardcode API keys in notebooks.
