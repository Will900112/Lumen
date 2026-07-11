"""ETL step 1: parse source PDFs into Markdown with LlamaParse.

Input:  backend/data/raw/<book>.pdf   (gitignored, copyrighted material)
Output: backend/data/parsed/<book>.md
"""

import os

import nest_asyncio
from dotenv import load_dotenv
from llama_parse import LlamaParse

nest_asyncio.apply()
load_dotenv()

DATA_DIR = os.path.dirname(__file__)
RAW_DIR = os.path.join(DATA_DIR, "raw")
PARSED_DIR = os.path.join(DATA_DIR, "parsed")

# output markdown filename -> source PDF filename
BOOKS = {
    "modern_nutrition.md": (
        "Modern Nutrition in Health and Disease (Katherine L. Tucker, "
        "Christopher P. Duggan etc.) (z-library.sk, 1lib.sk, z-lib.sk).pdf"
    ),
    "nutritional_medicine.md": (
        "Nutritional Medicine (First Edition) (Alan Gaby MD) "
        "(z-library.sk, 1lib.sk, z-lib.sk).pdf"
    ),
    "stockleys_interactions.md": (
        "Stockleys Herbal Medicines Interactions (Elizabeth Williamson, "
        "Samuel Driver etc.) (z-library.sk, 1lib.sk, z-lib.sk).pdf"
    ),
}


def parse_book(parser: LlamaParse, md_name: str, pdf_name: str) -> None:
    output_path = os.path.join(PARSED_DIR, md_name)
    if os.path.exists(output_path):
        print(f"[skip] {md_name} already exists")
        return

    pdf_path = os.path.join(RAW_DIR, pdf_name)
    if not os.path.exists(pdf_path):
        print(f"[skip] source PDF not found: {pdf_name}")
        return

    print(f"[parse] {pdf_name}")
    documents = parser.load_data(pdf_path)
    full_text = "\n\n".join(doc.text for doc in documents)

    os.makedirs(PARSED_DIR, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"[done] {md_name}: {len(documents)} pages, {len(full_text):,} chars")


def main() -> None:
    parser = LlamaParse(
        api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
        result_type="markdown",
        verbose=True,
    )
    for md_name, pdf_name in BOOKS.items():
        parse_book(parser, md_name, pdf_name)


if __name__ == "__main__":
    main()
