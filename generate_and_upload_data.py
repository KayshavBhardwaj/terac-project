import os
import time
import json
import random
import uuid
from tqdm import tqdm
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai

# --- Initialize Firebase ---
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
print("Successfully connected to Firestore.")

# --- Initialize Gemini ---
try:
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-lite')
    print("Successfully connected to Google Gemini.")
except KeyError:
    print("ERROR: GEMINI_API_KEY environment variable not set.")
    exit()

# --- Configuration ---
NUM_USERS_TO_GENERATE = 100
BATCH_SIZE = 10 


PROMPT_TEMPLATE = f"""
Generate {BATCH_SIZE} unique and diverse synthetic user profiles for Terac, a B2B tech company.
The output should be a single, valid JSON array where each object is a user profile.

CRITICAL INSTRUCTIONS:
- The 'last_feedback_summary' should be a realistic user complaint, question, or feedback.
- Set 'assigned_interviewer_agent' to "N/A" for all generated users.

Here is the required JSON structure. Do not output anything other than the JSON array.

[
  {{
    "contact_name": "string",
    "contact_email": "string (valid email format)",
    "company_name": "string",
    "company_size": "string (one of '1-10', '11-50', '51-200', '201-1000', '1000+')",
    "industry": "string",
    "product_tier": "string (one of 'Free', 'Pro', 'Enterprise')",
    "monthly_spend_usd": float,
    "user_sentiment_score": float (from -1.0 to 1.0),
    "last_feedback_summary": "string (1-2 sentences of plausible user feedback)",
    "assigned_interviewer_agent": "N/A"
  }}
]
"""

# --- Main Data Generation and Upload Loop ---
print(f"Generating {NUM_USERS_TO_GENERATE} user profiles using Gemini...")

all_generated_users = []
num_batches = (NUM_USERS_TO_GENERATE + BATCH_SIZE - 1) // BATCH_SIZE

for i in tqdm(range(num_batches), desc="Generating Batches"):
    retries = 0
    max_retries = 3
    generation_successful = False

    while not generation_successful and retries < max_retries:
        try:
            response = model.generate_content(PROMPT_TEMPLATE)
            response_text = response.text.strip().replace('```json', '').replace('```', '')
            users_batch = json.loads(response_text)
            all_generated_users.extend(users_batch)
            generation_successful = True
        except Exception as e:
            retries += 1
            wait_time = random.uniform(5, 10)
            tqdm.write(f" -> An error occurred: {e}.")
            if retries < max_retries:
                tqdm.write(f" -> Retrying in {wait_time:.1f} seconds... (Attempt {retries}/{max_retries})")
                time.sleep(wait_time)
            else:
                tqdm.write(f" -> Max retries reached. Could not generate this batch. Skipping.")
    time.sleep(1.5)

print("\nData generation complete. Uploading to Firestore...")

# --- Uploading to Firestore ---
for user_data in tqdm(all_generated_users, desc="Uploading Users"):
    try:
        user_id = str(uuid.uuid4())
        user_data['user_id'] = user_id
        
        doc_ref = db.collection('users').document(user_id)
        doc_ref.set(user_data)
    except Exception as e:
        tqdm.write(f" -> Could not upload user {user_data.get('contact_name')}. Error: {e}")

print("\nLLM-powered data generation and upload complete!")