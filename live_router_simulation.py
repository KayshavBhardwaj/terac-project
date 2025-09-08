import os
import time
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
from google.api_core import exceptions


# 1. Connect to Firestore
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    app = firebase_admin.initialize_app(cred, name='live-router-app')
    db = firestore.client(app)
    print("✅ Listener connected to Firestore.")
except ValueError: 
    app = firebase_admin.get_app(name='live-router-app')
    db = firestore.client(app)
    print("✅ Listener re-connected to existing Firestore session.")

# 2. Connect to the Gemini
try:
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-lite')
    print("✅ Listener connected to Google Gemini for live analysis.")
except KeyError:
    print("❌ CRITICAL ERROR: GEMINI_API_KEY environment variable not set.")
    exit()

# 3. Define the "AI Interviewer Agents"
INTERVIEWER_AGENTS = {
    "Product & Features Team": {"focus": ["Feature Request", "Performance Issue"]},
    "UX Research Team": {"focus": ["UI/UX Experience"]},
    "Sales & Billing Team": {"focus": ["Pricing/Billing"]},
}


def get_topic_from_transcript(transcript: str):
    prompt = f"""
    Analyze the user feedback transcript and classify it into ONE category:
    - UI/UX Experience
    - Feature Request
    - Pricing/Billing
    - Performance Issue
    Transcript: "{transcript}"
    Return ONLY the category name.
    """
    retries = 0
    max_retries = 2
    while retries < max_retries:
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except exceptions.ResourceExhausted as e:
            print(f"    ⚠️ RATE LIMIT HIT. Waiting 60 seconds before retrying. Error: {e}")
            time.sleep(60)
            retries += 1
        except Exception:
            # For other errors, try one more time after a short delay
            time.sleep(5)
            retries += 1
            
    return "Uncategorized"

def get_interviewer_agent(topic: str):
    for agent, details in INTERVIEWER_AGENTS.items():
        if topic in details["focus"]:
            return agent
    return "General Queue"

# --- REAL-TIME LISTENER LOGIC ---

def on_new_user_snapshot(doc_snapshot, changes, read_time):
    for change in changes:
        if change.type.name == 'ADDED':
            user_doc = change.document
            user_data = user_doc.to_dict()
            user_name = user_data.get("contact_name", "Unknown User")
            transcript = user_data.get("last_feedback_summary", "")

            print("\n--- [New User Detected!] ---")
            print(f"👤 INCOMING: '{user_name}' (ID: {user_doc.id})")

            if not transcript:
                print("    ⏩ SKIPPING: No transcript data found.")
                user_doc.reference.update({'assigned_interviewer_agent': 'Skipped - No Transcript'})
                continue

            print("    🧠 Analyzing transcript with Gemini...")
            inferred_topic = get_topic_from_transcript(transcript)
            print(f"    ✅ Analysis Complete. Inferred Topic: [{inferred_topic}]")

            # If the topic is uncategorized, wait a bit before processing the next user
            if inferred_topic == "Uncategorized":
                print("    ⚠️ Uncategorized result. Pausing for 10 seconds.")
                time.sleep(10)

            assigned_agent = get_interviewer_agent(inferred_topic)
            print(f"    ➡️ Routing to: {assigned_agent}")

            try:
                user_doc.reference.update({'assigned_interviewer_agent': assigned_agent})
                print(f"    💾 Firestore updated successfully.")
            except Exception as e:
                print(f"    ❌ Failed to update Firestore: {e}")
            
            # General rate-limiting delay to stay under 30 req/min
            time.sleep(2.5)

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    query_for_new_users = db.collection('users').where('assigned_interviewer_agent', '==', 'N/A')
    query_watch = query_for_new_users.on_snapshot(on_new_user_snapshot)

    print("\n--- Live Router is Active ---")
    print("Listening for new, unprocessed users...")
    print("Press Ctrl+C to stop the listener.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n--- Listener stopped by user. ---")