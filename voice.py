import os
import asyncio
import edge_tts

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

async def synthesize(text: str, filename: str = "response.mp3") -> str:
    path = os.path.join(AUDIO_DIR, filename)
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    await communicate.save(path)
    return path

def tts(text: str, filename: str = "response.mp3") -> str:
    return asyncio.run(synthesize(text, filename))
