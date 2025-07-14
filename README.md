
# Insta Chat Data Extractor

This project extracts structured customer information from Instagram (and other platform) chat export JSON files using LLMs (such as Groq LLaMA 3, Llama-3-8B-Instruct, etc).  
It supports translation, product/discount extraction, and incremental output saving.

---

## Features

- Extracts: customer name, folder name, phone, address, products, discounts, language, inquiry platform, and more.
- Supports non-English chats (auto-translates to English before extraction).
- Incrementally saves results to `output/extracted_customers.json` after each file.
- Prompt and model are configurable.
- Works with local LLMs (Llama.cpp GGUF) or API-based models (Groq, OpenAI, etc).

---

## Project Structure

```
.
├── data/                       # Input chat JSON files (organized in folders)
├── models/                     # Local GGUF models (if using Llama.cpp)
├── output/
│   └── extracted_customers.json # Output file (results)
├── prompts/
│   └── extract_customer_info.txt # Prompt template for extraction
├── process_chats.py            # Main extraction script
├── .env                        # API keys (if needed)
└── README.md                   # This file
```

---

## Setup

1. **Clone the repo and install dependencies:**
   ```bash
   git clone <repo-url>
   cd insta-chat-data-extractor
   python -m venv llm_env
   source llm_env/bin/activate
   pip install -r requirements.txt
   ```

2. **Set up your `.env` file** (if using API models like Groq/OpenAI):
   ```
   GROQ_API_KEY=your_groq_api_key
   ```

3. **Download a model (if using local Llama.cpp):**
   - For Llama-3-8B-Instruct:
     ```bash
     python download_llama3.py
     ```
   - Or manually download a GGUF model from [TheBloke on HuggingFace](https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF) and place it in `models/`.

4. **Prepare your prompt:**
   - Edit `prompts/extract_customer_info.txt` to customize extraction instructions.

5. **Place your chat JSON files in the `data/` directory.**

---

## Usage

```bash
python process_chats.py
```

- The script will process all `.json` files in `data/` (including subfolders).
- Results are saved incrementally to `output/extracted_customers.json`.

---

## Output Example

```json
[
  {
    "customer_name": "Kari",
    "folder_name": "kari_404820900998026",
    "phone": "",
    "address": "Chiclayo",
    "products": [
      {
        "name": "leggins seduction",
        "quantity": 1,
        "price": "S/.60"
      }
    ],
    "discounts": [],
    "language": "es",
    "inquiry_platform": "Instagram",
    "interested": true,
    "source_file": "message_1.json"
  }
]
```

---

## Customization

- **Prompt:** Edit `prompts/extract_customer_info.txt` to change extraction logic or output fields.
- **Model:** Change `MODEL_PATH` in `process_chats.py` to use a different GGUF model.
- **API Model:** Change the `llm` initialization in `process_chats.py` to use Groq, OpenAI, etc.

---

## Troubleshooting

- **Model download errors:**  
  Double-check repo and filename on HuggingFace.  
  Make sure you are logged in (`huggingface-cli login`) for gated models.

- **Extraction issues:**  
  Improve your prompt with more explicit instructions and examples.

- **Memory issues:**  
  Use a smaller quantization (Q4_K_M, Q5_K_M) or a smaller model (Phi-3, Mistral-7B).

---

## Credits

- [LangChain](https://github.com/langchain-ai/langchain)
- [TheBloke GGUF Models](https://huggingface.co/TheBloke)
- [deep-translator](https://github.com/nidhaloff/deep-translator)

---

## License

MIT License
