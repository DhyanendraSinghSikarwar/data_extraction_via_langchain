import os
import json
from langchain.prompts import PromptTemplate
from deep_translator import GoogleTranslator
from langchain_community.llms import LlamaCpp

DATA_DIR = "./data/"
OUTPUT_FILE = "output/extracted_customers.json"
MODEL_PATH = 'models/mistral-7b-instruct-v0.2.Q4_K_M.gguf'
PROMPT_PATH = "prompts/extract_customer_info.txt"

# Load LLM
llm = LlamaCpp(
    model_path=MODEL_PATH,
    n_ctx=2048,
    temperature=0.7,
    max_tokens=512,
    verbose=False
)

# Load prompt from file
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    prompt_template_str = f.read()

prompt = PromptTemplate(
    input_variables=["chat"],
    template=prompt_template_str
)
chain = prompt | llm

# Helper: Translate to English
def translate_to_english(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except Exception:
        return text  # fallback

# Helper: Clean and format chat
def format_chat(messages):
    dialogue = []
    for msg in messages:
        if 'content' in msg:
            speaker = msg.get("sender_name", "Unknown")
            content = translate_to_english(msg["content"])
            dialogue.append(f"{speaker}: {content}")
    return "\n".join(dialogue)

# Ensure all required fields are present and set defaults if missing
def ensure_fields(result, customer_name, folder_name):
    template = {
        "customer_name": customer_name or "",
        "folder_name": folder_name or "",
        "phone": "",
        "address": "",
        "products": [],
        "language": "",
        "inquiry_platform": "",
        "interested": False
    }
    # Add missing keys with default values
    for key, default in template.items():
        if key not in result or result[key] is None:
            result[key] = default
    return result

# Main extraction
def extract_info_from_json_file(file_path, folder_name):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Extract customer name from participants
    participants = data.get("participants", [])
    customer_name = None
    for p in participants:
        if p.get("name") != "J-SPORT":
            customer_name = p.get("name")
            break

    formatted_chat = format_chat(data.get("messages", []))
    response = chain.invoke({"chat": formatted_chat})
    try:
        result = json.loads(response)
    except Exception:
        result = {"raw_output": response}
    # Always include customer_name and folder_name
    result = ensure_fields(result, customer_name, folder_name)
    return result

# Walk through folders
def process_all_jsons():
    results = []
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith(".json"):
                full_path = os.path.join(root, file)
                print(f"Processing: {full_path}")
                relative_path = os.path.relpath(root, DATA_DIR)
                folder_name = os.path.basename(relative_path)
                info = extract_info_from_json_file(full_path, folder_name)
                info["source_file"] = file
                results.append(info)
                # Write/update output file after each processed file
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Done! Extracted info saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_all_jsons()
