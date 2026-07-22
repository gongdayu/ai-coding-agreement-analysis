# Article-Code Binary Datasets

This folder contains public article-code binary datasets used for the GPT-4.1
Q1-Q4 agreement calculations.

Each row is one article-question-label comparison:

- `Article Number`: article identifier.
- `Question`: Q1, Q2, Q3, or Q4.
- `Label`: allowed code for that question.
- `AI`: binary indicator for whether GPT-4.1 selected the label.
- `Human`: binary indicator for whether the human coder selected the label.

These files are datasets, not summary result tables. TP, TN, FP, FN, and all
agreement metrics are calculated by the scripts in `analysis_code/`.
