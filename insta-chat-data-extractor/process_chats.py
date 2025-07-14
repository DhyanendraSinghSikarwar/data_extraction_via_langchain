import os
import json
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from deep_translator import GoogleTranslator
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from langchain_community.chat_models import ChatOpenAI
from encryption import encrypt_messages
import psycopg2
from psycopg2 import sql
import re

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DATABASE = os.getenv("PG_DATABASE")
PG_TABLE = os.getenv("PG_TABLE")

# Constants
DATA_DIR = "./data/"
PROMPT_PATH = "prompts/extract_customer_info.txt"

# Use Nous-Hermes-2-Mixtral-8x7B-DPO via Groq
llm = ChatOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    model="llama3-70b-8192",
    temperature=0.2,
    max_tokens=1024
)

# Load prompt
def load_prompt():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

prompt = PromptTemplate(
    input_variables=["chat"],
    template=load_prompt()
)

chain: Runnable = prompt | llm | StrOutputParser()

def translate_to_english(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except Exception:
        return text

def format_chat(messages):
    dialogue = []
    for msg in messages:
        if 'content' in msg:
            speaker = msg.get("sender_name", "Unknown")
            content = translate_to_english(msg["content"])
            dialogue.append(f"{speaker}: {content}")
    return "\n".join(dialogue)

def ensure_fields(result, customer_name, folder_name):
    template = {
        "customer_name": customer_name or "",
        "folder_name": folder_name or "",
        "phone": "",
        "address": "",
        "products": [],
        "discounts": [],
        "language": "",
        "inquiry_platform": "",
        "interested": False,
        "other_info": ""
    }
    for key, default in template.items():
        if key not in result or result[key] is None:
            result[key] = default
    return result

def setup_postgres():
    conn = psycopg2.connect(
        dbname="postgres",
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (PG_DATABASE,))
    if not cur.fetchone():
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(PG_DATABASE)))
    cur.close()
    conn.close()

    conn = psycopg2.connect(
        dbname=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT
    )
    cur = conn.cursor()
    create_table_query = sql.SQL("""
    CREATE TABLE IF NOT EXISTS {} (
        id SERIAL PRIMARY KEY,
        customer_name TEXT,
        folder_name TEXT,
        phone TEXT,
        address TEXT,
        products TEXT,
        discounts TEXT,
        language TEXT,
        inquiry_platform TEXT,
        interested BOOLEAN,
        other_info TEXT,
        all_messages_english_encrypted TEXT
    )
    """).format(sql.Identifier(PG_TABLE))
    cur.execute(create_table_query)
    conn.commit()
    cur.close()
    conn.close()

def insert_customer_to_postgres(customer):
    def safe_str(val):
        return str(val) if val is not None else ""

    conn = psycopg2.connect(
        dbname=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT
    )
    cur = conn.cursor()
    cur.execute(
        sql.SQL("""
        INSERT INTO {} (
            customer_name, folder_name, phone, address, products, discounts,
            language, inquiry_platform, interested, other_info, all_messages_english_encrypted
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """).format(sql.Identifier(PG_TABLE)),
        (
            safe_str(customer.get("customer_name")),
            safe_str(customer.get("folder_name")),
            safe_str(customer.get("phone")),
            safe_str(customer.get("address")),
            json.dumps(customer.get("products", []), ensure_ascii=False),
            json.dumps(customer.get("discounts", []), ensure_ascii=False),
            safe_str(customer.get("language")),
            safe_str(customer.get("inquiry_platform")),
            customer.get("interested") if isinstance(customer.get("interested"), bool) else False,
            safe_str(customer.get("other_info")),
            safe_str(customer.get("all_messages_english_encrypted")),
        )
    )
    conn.commit()
    cur.close()
    conn.close()

def extract_info_from_json_file(file_path, folder_name):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    participants = data.get("participants", [])
    customer_name = next((p["name"] for p in participants if p["name"] != "J-SPORT"), None)

    messages = data.get("messages", [])
    formatted_chat = format_chat(messages)
    all_messages_english = [
        f"{msg.get('sender_name', 'Unknown')}: {translate_to_english(msg['content'])}"
        for msg in messages if 'content' in msg
    ]

    try:
        # print("[DEBUG] Invoking LLM...")
        response = chain.invoke({"chat": formatted_chat})
        # print(f"[DEBUG] Raw model response:\n{response}\n")
        # Extract JSON from code block if present
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", response)
        if match:
            json_str = match.group(1)
        else:
            # Fallback: try to find the first {...} block
            match = re.search(r"(\{[\s\S]+\})", response)
            json_str = match.group(1) if match else response
        result = json.loads(json_str)
    except Exception as e:
        print(f"[ERROR] Failed to parse model output: {e}")
        result = {}

    result = ensure_fields(result, customer_name, folder_name)
    result["all_messages_english_encrypted"] = encrypt_messages(all_messages_english)
    return result

def process_all_jsons():
    setup_postgres()
    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith(".json"):
                full_path = os.path.join(root, file)
                print(f"Processing: {full_path}")
                relative_path = os.path.relpath(root, DATA_DIR)
                folder_name = os.path.basename(relative_path)
                info = extract_info_from_json_file(full_path, folder_name)
                info["source_file"] = file
                # print(f"[DEBUG] Final extracted info:\n{json.dumps(info, indent=2, ensure_ascii=False)}")
                insert_customer_to_postgres(info)
    print("✅ Done! All extracted info inserted into Postgres.")

if __name__ == "__main__":
    process_all_jsons()
