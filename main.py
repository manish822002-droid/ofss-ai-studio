import os
import re
import time
import tempfile
from collections import defaultdict, deque
from pathlib import Path

import edge_tts
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

app = FastAPI(title="OFSS AI Studio TTS API", version="1.0.0")

# Demo-friendly CORS. For a public production site, set ALLOWED_ORIGINS to your
# exact frontend origins, separated by commas, e.g. https://ai.ofssbiharboard.com
origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

VOICES = {
    "en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural",
    "en-US-ChristopherNeural", "en-GB-SoniaNeural", "en-GB-RyanNeural",
    "hi-IN-SwaraNeural", "hi-IN-MadhurNeural",
}
RATES = {"-10%", "+0%", "+10%", "+20%"}
recent = defaultdict(deque)
WINDOW_SECONDS = 60
MAX_REQUESTS_PER_MINUTE = 8

class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    voice: str = "en-US-AriaNeural"
    rate: str = "+0%"

@app.get("/")
async def home():
    return {"service": "OFSS AI Studio TTS API", "status": "ok", "endpoint": "/api/tts"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/tts")
async def make_tts(payload: TTSRequest, request: Request):
    client = request.client.host if request.client else "unknown"
    now = time.time()
    q = recent[client]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    if len(q) >= MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute and try again.")
    q.append(now)

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please enter some text.")
    if payload.voice not in VOICES:
        raise HTTPException(status_code=400, detail="Please choose a supported voice.")
    if payload.rate not in RATES:
        raise HTTPException(status_code=400, detail="Please choose a supported speaking speed.")

    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            path = f.name
        communicator = edge_tts.Communicate(text, payload.voice, rate=payload.rate)
        await communicator.save(path)
        if not os.path.exists(path) or os.path.getsize(path) < 100:
            raise RuntimeError("The speech provider returned no usable audio.")
        return FileResponse(
            path,
            media_type="audio/mpeg",
            filename="ofss-ai-studio.mp3",
            background=BackgroundTask(lambda: os.path.exists(path) and os.remove(path)),
        )
    except HTTPException:
        if path and os.path.exists(path):
            os.remove(path)
        raise
    except Exception as exc:
        if path and os.path.exists(path):
            os.remove(path)
        # Keep internal exception details out of the public response.
        raise HTTPException(status_code=502, detail="The speech provider could not generate audio right now. Please retry shortly.") from exc
