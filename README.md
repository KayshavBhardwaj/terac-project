# Terac Assignment: User Data Generation & Live Routing System

## Project Summary

A complete system for generating high quality synthetic user data, and routing those users in real-time to an AI interviewer that suits their needs.

## Architecture & Design Choices

System has 2 main components, one is the data generation, and the other is the data routing.

1.  **Data Generator (generate_and_upload_data.py):**
    *   Uses Gemini to generate 100 realistic and non-monotonic user profiles.
    *   Generates data such as interview transcript, sentiment, and other factors.
    *   Stores these users in a Firestore database.

2.  **Live Router (live_router_simulation.py):**
    *   A perpetually running Python script that detects new users added to the Firestore (especially those with assigned_interviewer_agent: 'N/A'), basically those who haven't been assigned an interviewer yet.
    *   When a new user is detected, it takes their raw feedback transcript and uses Gemini to determine which AI interviewer would be best for their needs.
    *   Based on the AI's classification, it routes the user to the appropriate interviewer team by adding a data entry into the FireStore for the user's assigned_interview_agent.
    *   Updates the user's record in Firestore with the routing decision.

## How to Run the Project

**Prereqs:**
*   Python
*   A Google Firestore projetc.
*   A Gemini API Key.

**1. Setup:**
*   Clone the repository.
*   Put Firebase service account key in the main directory and name it serviceAccountKey.json.
*   Install requirements by running the following in terminal: pip install -r requirements.txt
*   Set your Gemini API key as an environment variable by running:    export GEMINI_API_KEY='YOUR_API_KEY_HERE'
  

**2. Run the Workflow:**
*   **(Step 1) Generate Data:** Run the generator script to populate Firestore:    python generate_and_upload_data.py
*   **(Step 2) Start the Live Router:** Run the listener script. It will process all existing users and then wait for new ones:    python live_router_simulation.py
