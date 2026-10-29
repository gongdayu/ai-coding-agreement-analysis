"""Step 1: extract the text of every PDF in a folder into one JSON file.

Usage:
    python scripts/parse_pdfs.py --pdf-dir <folder of PDFs> --out <pdf_text.json>

The output maps article_id (the PDF file name without ".pdf") to the article
text. Every model reads this same file, so all models receive identical input.
The SHA-256 of the output is printed and written next to it (<out>.sha256).
"""
import argparse
import hashlib
import json
import os

from langchain_community.document_loaders import PyPDFLoader


def extract_pdfs_to_json(pdf_folder_path, json_path):
    """
    Extracts text from all PDFs in the given folder and saves them to a JSON file.

    Args:
        pdf_folder_path (str): Path to the folder containing PDF files.
        json_path (str): Path to the JSON file to save the extracted texts.
    """
    all_pdfs = {}
    for file_name in sorted(os.listdir(pdf_folder_path)):
        if file_name.lower().endswith('.pdf'):
            pdf_idx = os.path.splitext(file_name)[0]
            if pdf_idx in all_pdfs:
                raise ValueError(f"Duplicate article ID: {pdf_idx}")
            loader = PyPDFLoader(os.path.join(pdf_folder_path, file_name))
            document = loader.load()
            pdf_text = ''
            for page in document:
                pdf_text += page.page_content
            all_pdfs[pdf_idx] = pdf_text
            if not pdf_text.strip():
                raise ValueError(f"No extracted text: {file_name}; OCR/visual content is not handled")
    if not all_pdfs:
        raise ValueError("No PDF files found")
    with open(json_path, 'w', encoding='utf-8') as fp:
        json.dump(all_pdfs, fp)
    return all_pdfs


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf-dir", required=True, help="Folder containing the PDF files")
    ap.add_argument("--out", required=True, help="Output JSON file (article_id -> text)")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    all_pdfs = extract_pdfs_to_json(args.pdf_dir, args.out)
    digest = file_sha256(args.out)
    with open(args.out + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{digest}  {os.path.basename(args.out)}\n")
    print(f"Extracted {len(all_pdfs)} PDFs -> {args.out}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
