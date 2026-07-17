import os
import asyncio
import uuid
import edge_tts

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

async def synthesize(text: str) -> str:
    filename = f"{uuid.uuid4().hex}.mp3"
    path = os.path.join(AUDIO_DIR, filename)
    try:
        communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
        await communicate.save(path)
    except Exception as e:
        raise RuntimeError(f"TTS failed: {e}")
    return path

def tts(text: str) -> str:
    return asyncio.run(synthesize(text))
