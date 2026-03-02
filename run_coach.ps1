# Navigate to this script’s directory
Set-Location -Path $PSScriptRoot

# Activate virtual environment if it exists
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    . .\venv\Scripts\Activate.ps1
}

# Run Streamlit
streamlit run ui\coach_bot_ui.py