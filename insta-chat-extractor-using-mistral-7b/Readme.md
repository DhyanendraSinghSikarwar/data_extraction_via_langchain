Here's a complete `README.md` for your project, updated to reflect the use of a **separate folder and file for the prompt template**, as well as detailed setup and usage instructions.

---

## 📦 Instagram Chat Data Extractor (Offline LLM with LangChain)

This project uses an **open-source LLM** (Mistral 7B Instruct) running locally via `llama-cpp-python` and LangChain to extract structured customer data from multilingual Instagram chat exports (in JSON format).
It is fully **offline**, **open-source**, and suitable for machines with **16 GB RAM**.

---

### 📌 Features

* ✅ Reads all `.json` chat files from nested folders.
* 🌍 Translates messages (e.g., from Spanish) to English.
* 🧠 Uses LLM to extract structured data:

  * Customer name
  * Contact info
  * Products inquired
  * Products purchased
  * Delivery address (if mentioned)
* 🧾 Outputs structured results in `extracted_customers.json`
* 🆓 Uses open-source Mistral-7B-Instruct model locally.

---

### 🧠 Model Used

* **Model**: `mistral-7b-instruct-v0.1.Q4_K_M.gguf`
* **Source**: [TheBloke on HuggingFace](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF)
* **Quantization**: `Q4_K_M` (optimized for CPU, low RAM)
* **Framework**: `llama-cpp-python` with LangChain

---

### 🗂️ Folder Structure

```
instagram-chat-extractor/
├── data/                         # Input folder with subfolders containing .json chat files
│   └── customer1/
│       └── message_1.json
├── models/                       # Contains Mistral model file (.gguf)
│   └── mistral-7b-instruct.Q4_K_M.gguf
├── prompts/
│   └── chat_prompt.txt          # Custom LLM prompt in text file
├── process_chats.py             # Main Python script
├── requirements.txt             # Python dependencies
└── README.md
```

---

### 💬 Prompt Template (prompts/chat\_prompt.txt)

This file contains the LLM instruction. You can edit this to improve extraction quality.

```text
You are an assistant helping extract customer information from chat.

Here is the chat log (in English):

{chat}

Extract and return the following:
- Customer name
- Contact info (if any)
- Products asked about
- Products purchased (if mentioned)
- Delivery address (if mentioned)

Return the result as JSON.
```

---

### 🧪 Output Example (`extracted_customers.json`)

```json
[
  {
    "customer_name": "Karen Vasquez",
    "contact_info": null,
    "products_inquired": ["legging", "pantalón", "guantes"],
    "products_purchased": ["polo", "palazo"],
    "delivery_address": null,
    "source_file": "message_1.json"
  }
]
```

---

### 🛠️ Setup Instructions

#### 1. Clone the Repo and Install Dependencies

```bash
git clone <your-repo-url>
cd instagram-chat-extractor
pip install -r requirements.txt
```

#### 2. Download the Model (GGUF Format)

* 📦 [Download here](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF)
* Choose: `mistral-7b-instruct-v0.1.Q4_K_M.gguf`
* Move it to the `models/` directory.

#### 3. Prepare Chat Data

* Place all `.json` Instagram chat files inside `data/`, organized by customer folders.

#### 4. Run the Script

```bash
python process_chats.py
```

---

### 📄 Requirements

#### `requirements.txt`

```txt
langchain
llama-cpp-python
openai
tqdm
python-dotenv
deep-translator
```

Install with:

```bash
pip install -r requirements.txt
```

---

### 🔧 Configuration (Optional)

* You can modify the prompt in `prompts/chat_prompt.txt` to change the behavior of the LLM.
* Translations are handled by `deep-translator` (GoogleTranslator) by default.

---

### 💡 Tips

* For larger batch processing or performance, consider using a GPU with GGUF `Q6_K` or `Q8_0` models.
* To improve accuracy: fine-tune the prompt, remove duplicate chat lines, or summarize long threads before LLM input.

---

### 📃 License

This project is open-source under the MIT license. Use responsibly.

---

Would you like me to include an example `.json` file and `.txt` prompt for GitHub reference too?
