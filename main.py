
import os
import time
import tempfile
from collections import defaultdict, deque
from pathlib import Path

import edge_tts
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

app = FastAPI(title="OFSS AI Studio TTS API", version="1.1.0")

origins = [
    x.strip()
    for x in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if x.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

VOICES = {
    "en-US-AriaNeural", "en-US-GuyNeural",
    "en-US-JennyNeural", "en-US-ChristopherNeural",
    "en-GB-SoniaNeural", "en-GB-RyanNeural",
    "hi-IN-SwaraNeural", "hi-IN-MadhurNeural",
}

RATES = {"-10%", "+0%", "+10%", "+20%"}
recent = defaultdict(deque)
WINDOW_SECONDS = 60
MAX_REQUESTS_PER_MINUTE = 8
CHUNK_SIZE = 2800


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    voice: str = "en-US-AriaNeural"
    rate: str = "+0%"


def split_text(text):
    text = text.strip()
    chunks = []

    while len(text) > CHUNK_SIZE:
        limit = text[:CHUNK_SIZE]
        cut = max(
            limit.rfind(". "),
            limit.rfind("? "),
            limit.rfind("! "),
            limit.rfind("\n"),
        )

        if cut < CHUNK_SIZE // 2:
            cut = limit.rfind(" ")

        if cut <= 0:
            cut = CHUNK_SIZE

        chunks.append(text[:cut].strip())
        text = text[cut:].strip()

    if text:
        chunks.append(text)

    return chunks


@app.get("/", response_class=HTMLResponse)
async def home():
    html_path = Path(__file__).parent / "index.html"

    if not html_path.exists():
        raise HTTPException(
            status_code=500,
            detail="index.html file not found",
        )

    return FileResponse(html_path, media_type="text/html")


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
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute and try again.",
        )

    q.append(now)
    text = payload.text.strip()

    if not text:
        raise HTTPException(status_code=400, detail="Please enter some text.")

    if payload.voice not in VOICES:
        raise HTTPException(status_code=400, detail="Unsupported voice.")

    if payload.rate not in RATES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported speaking speed.",
        )

    output_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".mp3", delete=False
        ) as output:
            output_path = output.name

        chunks = split_text(text)

        with open(output_path, "wb") as combined:
            for chunk in chunks:
                with tempfile.NamedTemporaryFile(
                    suffix=".mp3", delete=False
                ) as part:
                    part_path = part.name

                try:
                    communicator = edge_tts.Communicate(
                        chunk,
                        payload.voice,
                        rate=payload.rate,
                    )
                    await communicator.save(part_path)

                    if os.path.getsize(part_path) < 100:
                        raise RuntimeError("Audio generation failed.")

                    with open(part_path, "rb") as audio:
                        combined.write(audio.read())
                finally:
                    if os.path.exists(part_path):
                        os.remove(part_path)

        if os.path.getsize(output_path) < 100:
            raise RuntimeError("No usable audio was generated.")

        return FileResponse(
            output_path,
            media_type="audio/mpeg",
            filename="ofss-ai-studio.mp3",
            background=BackgroundTask(
                lambda: os.path.exists(output_path)
                and os.remove(output_path)
            ),
        )

    except HTTPException:
        if output_path and os.path.exists(output_path):
            os.remove(output_path)
        raise

    except Exception as exc:
        if output_path and os.path.exists(output_path):
            os.remove(output_path)

        raise HTTPException(
            status_code=502,
            detail="Audio generation failed. Please retry with shorter text.",
        ) from exc
