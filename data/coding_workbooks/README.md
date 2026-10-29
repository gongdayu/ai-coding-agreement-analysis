# Fixed coding data

The three UTF-8 CSV files are analysis exports of the supplied RR2 renumbered coding workbooks. They contain the 100 public article IDs and Q1–Q8 Human/GPT answer strings. Original GPT strings are preserved, including out-of-codebook labels. No GPT answer was adjudicated or replaced during packaging. The five author-confirmed Human reference differences were aligned to the common reference in both GPT-4.1 files; the GPT-5.4 reference was already aligned.

Files: `m1_gpt41.csv` (GPT-4.1, Method 1); `m2_gpt41.csv` (GPT-4.1, Method 2); `m2_gpt54.csv` (GPT-5.4, Method 2). Method 1 Q6–Q8 answers are retained for provenance; downstream performance is not compared for that condition.

`../articles.csv` links the same IDs to bibliographic metadata. IDs are unique integers 1–100 in all files. The private original-to-new mapping is deliberately excluded. Use ID joins, never row position. CSV is used to remove workbook-specific formatting and permit execution without Excel; it is the sole published representation of these coding data.
