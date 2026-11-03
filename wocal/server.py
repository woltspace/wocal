"""One local server with OpenAI-style speech and transcription endpoints.

    POST /v1/audio/speech          {"input", "voice", "response_format"} -> audio
    POST /v1/audio/transcriptions  multipart "file" -> {"text"}

Each model loads once, in the background after the port opens, and lives on its
own single thread: neither model is safe to call from several threads, and an
mlx model must stay on the thread that loaded it. A request made while a model
is still loading waits for it.
"""

import asyncio
import io
import subprocess
import tempfile
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel

STT_MODEL = "mlx-community/parakeet-tdt-0.6b-v3"
TTS_MODEL = "pocket"
DEFAULT_VOICE = "alba"
# Built-in voices only: a request never makes the server fetch a URL or read a file.
VOICES = {
    "alba", "marius", "javert", "jean", "cosette", "fantine", "eponine", "azelma", "anna", "vera",
    "charles", "paul", "george", "mary", "jane", "michael", "eve",
    "estelle", "lola", "giovanni", "juergen", "rafael", "daan",
}
FORMATS = {  # response_format -> (ffmpeg args, content type)
    "opus": (["-c:a", "libopus", "-b:a", "32k", "-f", "ogg"], "audio/ogg"),
    "mp3": (["-c:a", "libmp3lame", "-b:a", "64k", "-f", "mp3"], "audio/mpeg"),
    "wav": (None, "audio/wav"),
}
MAX_INPUT_CHARS = 4096
MAX_UPLOAD_BYTES = 200 * 1024 * 1024
CHUNK_SECONDS = 30.0
FFMPEG_TIMEOUT_SECONDS = 300


def load_tts():
    from pocket_tts import TTSModel

    return TTSModel.load_model()


def load_stt():
    from mlx_audio.stt import load

    return load(STT_MODEL)


class Worker:
    """A model and the one thread allowed to touch it."""

    def __init__(self, loader):
        self.loader = loader
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.model = None
        self.loaded: Future | None = None

    def start(self) -> None:
        self.loaded = self.pool.submit(self._load)

    def _load(self) -> None:
        self.model = self.loader()

    def status(self) -> str:
        if self.loaded is None or not self.loaded.done():
            return "loading"
        return "failed" if self.loaded.exception() else "ready"

    async def run(self, job, *args):
        try:
            await asyncio.wrap_future(self.loaded)
        except Exception as exc:
            raise HTTPException(503, "the model could not be loaded; see the server log") from exc
        return await asyncio.get_running_loop().run_in_executor(self.pool, job, self.model, *args)


tts = Worker(lambda: load_tts())
stt = Worker(lambda: load_stt())
voice_states: dict = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    tts.start()
    stt.start()
    yield


app = FastAPI(title="Wocal", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
# This server has no key, so a web page must not reach it by rebinding a hostname to it.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "*.localhost"])


def ffmpeg(args: list[str], stdin: bytes | None = None) -> bytes:
    done = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", *args],
        input=stdin, capture_output=True, timeout=FFMPEG_TIMEOUT_SECONDS,
    )
    if done.returncode != 0:
        raise ValueError(done.stderr.decode(errors="replace").strip()[-300:])
    return done.stdout


class SpeechRequest(BaseModel):
    input: str
    voice: str = DEFAULT_VOICE
    model: str = TTS_MODEL
    response_format: str = "opus"


def _speak(model, text: str, voice: str) -> bytes:
    import scipy.io.wavfile

    if voice not in voice_states:
        voice_states[voice] = model.get_state_for_audio_prompt(voice)
    audio = model.generate_audio(voice_states[voice], text)
    wav = io.BytesIO()
    scipy.io.wavfile.write(wav, model.sample_rate, audio.numpy())
    return wav.getvalue()


@app.post("/v1/audio/speech")
async def speech(request: SpeechRequest) -> Response:
    if not request.input.strip() or len(request.input) > MAX_INPUT_CHARS:
        raise HTTPException(400, f"input must be 1 to {MAX_INPUT_CHARS} characters")
    if request.voice not in VOICES:
        raise HTTPException(400, f"unknown voice; one of {', '.join(sorted(VOICES))}")
    if request.response_format not in FORMATS:
        raise HTTPException(400, f"response_format must be one of {', '.join(FORMATS)}")
    wav = await tts.run(_speak, request.input, request.voice)
    args, content_type = FORMATS[request.response_format]
    if args is None:
        return Response(wav, media_type=content_type)
    encoded = await asyncio.to_thread(ffmpeg, ["-i", "pipe:0", *args, "pipe:1"], wav)
    return Response(encoded, media_type=content_type)


def _transcribe(model, path: str) -> str:
    return model.generate(path, chunk_duration=CHUNK_SECONDS).text.strip()


@app.post("/v1/audio/transcriptions")
async def transcriptions(file: UploadFile, response_format: str = Form("json")) -> Response:
    if response_format not in ("json", "text"):
        raise HTTPException(400, "response_format must be json or text")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, f"file must be 1 byte to {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    with tempfile.TemporaryDirectory(prefix="wocal-") as scratch:
        source, wav = Path(scratch) / "upload", Path(scratch) / "audio.wav"
        source.write_bytes(data)
        try:
            await asyncio.to_thread(ffmpeg, ["-i", str(source), "-ac", "1", "-ar", "16000", str(wav)])
        except ValueError as exc:
            raise HTTPException(400, "that file could not be read as audio") from exc
        text = await stt.run(_transcribe, str(wav))
    if response_format == "text":
        return PlainTextResponse(text)
    return JSONResponse({"text": text})


@app.get("/health")
def health() -> dict:
    return {"speech": tts.status(), "transcription": stt.status()}


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Wocal</title>
<style>body{margin:0;padding:32px 16px;background:#EDE8DE;color:#2a2622;font:16px/1.5 system-ui,sans-serif}
main{max-width:520px;margin:auto}h1{margin:0;color:#C4531E}p{color:#6b645b}b{color:#3A6644}</style></head>
<body><main><h1>Wocal</h1><p>Local vocal wolts. Nothing you say leaves this Mac.</p>
<div>Speech: <b id="speech">...</b></div><div>Transcription: <b id="transcription">...</b></div></main>
<script>
async function refresh() {
  try {
    const status = await (await fetch("health")).json();
    document.getElementById("speech").textContent = status.speech;
    document.getElementById("transcription").textContent = status.transcription;
  } catch { /* the next tick tries again */ }
}
refresh(); setInterval(refresh, 3000);
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return PAGE
