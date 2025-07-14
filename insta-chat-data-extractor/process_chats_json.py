import os
import re
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

# Initialize Groq Mixtral model (optimized for extraction)
llm = ChatOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    model="mixtral-8x7b-32768",
    temperature=0.2,  # Lower for precise extraction
    max_tokens=1024
)

# Regex patterns for validation
PHONE_REGEX = re.compile(r"(\+?\d[\d\- ]{7,}\d)")  # Matches +51 987654321 or 987654321
ADDRESS_KEYWORDS = ["av.", "avenue", "street", "calle", "sector", "city", "district", "reference"]

# Load and update prompt template
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    prompt_template_str = f.read()

# Enhanced prompt for better extraction
prompt_template_str += """
IMPORTANT:
1. Phone numbers MUST match one of these patterns: "+51 987654321", "987654321", "cel: 987654321".
2. Addresses MUST include at least a city or street name.
3. Return ONLY valid JSON. If a field is missing, use "" or [].
"""

prompt = PromptTemplate(
    input_variables=["chat"],
    template=prompt_template_str
)

chain: Runnable = prompt | llm | StrOutputParser()

def translate_to_english(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except Exception:
        return text

def extract_phone_numbers(text):
    """Fallback regex phone extraction from customer messages"""
    return list(set(PHONE_REGEX.findall(text)))  # Deduplicate

def validate_address(address):
    """Check if address contains at least one keyword"""
    if not address:
        return ""
    return address if any(kw in address.lower() for kw in ADDRESS_KEYWORDS) else ""

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
        "language": "es",  # Default for Spanish chats
        "inquiry_platform": "",
        "interested": False,
        "other_info": ""
    }
    # Apply template defaults
    for key, default in template.items():
        if key not in result or result[key] is None:
            result[key] = default
    
    # Post-process phone and address
    if not result["phone"]:
        result["phone"] = ", ".join(extract_phone_numbers(result.get("other_info", "")))
    result["address"] = validate_address(result["address"])
    
    return result

def setup_postgres():
    """Initialize PostgreSQL database and table"""
    conn = psycopg2.connect(
        dbname="postgres",
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # Create database if not exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (PG_DATABASE,))
    if not cur.fetchone():
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(PG_DATABASE)))
    
    # Create table
    conn = psycopg2.connect(
        dbname=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT
    )
    cur = conn.cursor()
    cur.execute(sql.SQL("""
    CREATE TABLE IF NOT EXISTS {} (
        id SERIAL PRIMARY KEY,
        customer_name TEXT,
        folder_name TEXT,
        phone TEXT,
        address TEXT,
        products JSONB,
        discounts JSONB,
        language TEXT,
        inquiry_platform TEXT,
        interested BOOLEAN,
        other_info TEXT,
        all_messages_english_encrypted TEXT,
        source_file TEXT
    )
    """).format(sql.Identifier(PG_TABLE)))
    conn.commit()
    cur.close()
    conn.close()

def insert_customer_to_postgres(customer):
    """Insert extracted data into PostgreSQL"""
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
            language, inquiry_platform, interested, other_info, 
            all_messages_english_encrypted, source_file
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """).format(sql.Identifier(PG_TABLE)),
        (
            customer["customer_name"],
            customer["folder_name"],
            customer["phone"],
            customer["address"],
            json.dumps(customer["products"]),
            json.dumps(customer["discounts"]),
            customer["language"],
            customer["inquiry_platform"],
            customer["interested"],
            customer["other_info"],
            customer["all_messages_english_encrypted"],
            customer.get("source_file", "")
        )
    )
    conn.commit()
    cur.close()
    conn.close()

def extract_info_from_json_file(file_path, folder_name):
    """Process a single chat JSON file"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    participants = data.get("participants", [])
    customer_name = next((p["name"] for p in participants if p["name"] != "J-SPORT"), None)

    messages = data.get("messages", [])
    formatted_chat = format_chat(messages)
    all_messages_english = [translate_to_english(msg["content"]) for msg in messages if 'content' in msg]

    try:
        response = chain.invoke({"chat": formatted_chat})
        result = json.loads(response.strip())
    except json.JSONDecodeError:
        print(f"⚠️ Failed to parse JSON for {file_path}. Using fallback extraction.")
        result = {"other_info": formatted_chat}  # Fallback

    result = ensure_fields(result, customer_name, folder_name)
    result["all_messages_english_encrypted"] = encrypt_messages("\n".join(all_messages_english))
    result["source_file"] = os.path.basename(file_path)
    return result

def process_all_jsons():
    """Batch process all JSON files in DATA_DIR"""
    setup_postgres()
    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith(".json"):
                full_path = os.path.join(root, file)
                print(f"Processing: {full_path}")
                folder_name = os.path.basename(root)
                try:
                    info = extract_info_from_json_file(full_path, folder_name)
                    insert_customer_to_postgres(info)
                except Exception as e:
                    print(f"❌ Error processing {file}: {str(e)}")
    print("✅ All data processed and saved to PostgreSQL.")

if __name__ == "__main__":
    process_all_jsons()