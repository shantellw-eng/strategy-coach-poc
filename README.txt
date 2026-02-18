# Strategy Statement Coach (POC)

## Files
- coach_bot_ui.py - Streamlit app (front-end + OpenAI call)
- system_prompt.txt - your system prompt (paste the full prompt here)
- requirements.txt - dependencies

## Quick start (Windows PowerShell)
1) Create and activate a venv:
   python -m venv venv
   .\venv\Scripts\activate

2) Install dependencies:
   pip install -r requirements.txt

3) Set your API key (then restart PowerShell):
   setx OPENAI_API_KEY "YOUR_KEY_HERE"

4) Run the app:
   streamlit run coach_bot_ui.py

## Notes
- The app expects the assistant to append a <STATE_JSON>...</STATE_JSON> block on every reply.
- The sidebar shows the extracted Objective / Scope / Advantage and assumptions.
- Use the 'Board-level' toggle to increase sharpening intensity.
