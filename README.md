# Sotti

A local screenshot-to-code pipeline daemon. Watches a directory for screenshots, groups them, and uses an AI orchestrator to extract problem statements, which a sub-agent then implements as Java code. 

## 1. Setup on a New Machine

1. **Install UV** (if you don't already have it):
   
       pip install uv

2. **Sync Dependencies**:
   Navigate to the project root and run:
   
       uv sync

3. **Configure Settings**:
   Copy the example config and add your API keys:
   
       cp .env.example .env
   Open `.env` and fill in:
   - `GEMINI_API_KEY`
   - `WATCH_DIR` (The folder where screenshots are saved)
   - *Optional:* Change `SERVER_HOST` or `SERVER_PORT` if needed.

## 2. Running Sotti

To start the daemon and the web UI efficiently, always use `uv` directly from the project root:

    uv run python -m src.main

The console will print out the local and network URLs you can use to access the UI.

## 3. Accessing Sotti from your Phone (Windows Firewall)

By default, the server binds to `0.0.0.0` (all networks) on port `8000`. However, **Windows Firewall will block incoming connections by default.**

To allow your phone (or other devices on the same Wi-Fi) to connect:

1. Open **PowerShell or Command Prompt as an Administrator**.
2. Run the following command exactly:

    netsh advfirewall firewall add rule name="Sotti Port 8000" dir=in action=allow protocol=TCP localport=8000

3. Find the "**Network**" URL printed in Sotti's startup banner (e.g., `http://192.168.0.187:8000`) and open it in your phone's browser.
