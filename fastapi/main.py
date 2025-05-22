from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import requests

logger = logging.getLogger(__name__)
app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def serve_html():
    base_dir = Path(__file__).resolve().parents[1]  # Project root
    html_path = base_dir / "rasafiles" / "frontend.html"
    print(f"📂 Checking HTML path: {html_path}")

    if html_path.exists():
        logger.info("✅ frontend.html successfully loaded.")
        return HTMLResponse(content=html_path.read_text(), status_code=200)
    else:
        logger.error("❌ frontend.html not found.")
        return HTMLResponse(content="File not found", status_code=404)


@app.post("/chat")
async def chat_with_rasa(request: Request):
    data = await request.json()
    message = data.get("message", "")
    
    rasa_url = "http://localhost:5005/webhooks/rest/webhook"
    response = requests.post(rasa_url, json={"sender": "user", "message": message})

    rasa_response = response.json()

    # Join all text parts from rasa responses
    reply_parts = [msg["text"] for msg in rasa_response if "text" in msg]
    full_reply = "\n\n".join(reply_parts) if reply_parts else "No response from bot."

    return JSONResponse(content={"reply": full_reply})
