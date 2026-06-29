import os
import nest_asyncio
from dotenv import load_dotenv
from llama_parse import LlamaParse

nest_asyncio.apply()
load_dotenv()

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "parsed")

def parse_pdf():
    pdf_path = os.path.join(
        os.path.dirname(__file__),
        "raw",
        "Stockleys Herbal Medicines Interactions (Elizabeth Williamson, Samuel Driver etc.) (z-library.sk, 1lib.sk, z-lib.sk).pdf"
    )
    output_path = os.path.join(OUTPUT_DIR, "stockleys_interactions.md")

    if os.path.exists(output_path):
        print("⏭ 已存在，跳過")
        return

    print("開始解析 Stockley's Interactions...")

    parser = LlamaParse(
        api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
        result_type="markdown",
        verbose=True
    )

    documents = parser.load_data(pdf_path)
    print(f"解析完成，共 {len(documents)} 頁")

    full_text = "\n\n".join([doc.text for doc in documents])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"✅ 已存到: {output_path}")
    print(f"總字數: {len(full_text):,}")

if __name__ == "__main__":
    parse_pdf()