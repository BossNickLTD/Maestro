from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from groq import Groq
import os
import json
from datetime import datetime
from menu_utils import load_menu, validate_order, build_menu_prompt
from printer import print_order
from voice import tts

app = FastAPI(title="Maestro API")

audio_dir = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(audio_dir, exist_ok=True)
app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")

env_path = os.path.join(os.path.dirname(__file__), ".env")
with open(env_path) as f:
    for line in f:
        if line.startswith("GROQ_API_KEY="):
            os.environ["GROQ_API_KEY"] = line.strip().split("=", 1)[1]

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
menu = load_menu()

COUNTER_PATH = os.path.join(os.path.dirname(__file__), "_counter.json")
def next_order_num():
    num = 1
    if os.path.exists(COUNTER_PATH):
        with open(COUNTER_PATH) as f:
            num = json.load(f).get("last", 0) + 1
    with open(COUNTER_PATH, "w") as f:
        json.dump({"last": num}, f)
    return num

MENU_PROMPT = f"""Ты — AI-официант. Извлеки заказ из сообщения.

Меню:
{build_menu_prompt(menu)}

Правила:
1. В items — только названия из меню
2. Слова-описания ("большой", "свежий", "горячий" и т.п.) — игнорируй, НЕ пиши в unknown
3. Ингредиенты, которые уже описаны в modifiers (молоко, сахар, лимон) — не пиши в unknown
4. В unknown — пиши только то, чего реально нет в меню (например "борщ", "пельмени")
5. Ответь ТОЛЬКО JSON

Формат:
{{"items": [{{"name": "из меню", "quantity": число, "modifiers": {{}}}}], "unknown": []}}"""

class OrderRequest(BaseModel):
    text: str
    table: int = 0

class ItemOut(BaseModel):
    name: str
    quantity: int
    price: int
    modifiers: dict = {}

class OrderOut(BaseModel):
    items: list[ItemOut]
    errors: list[str] = []
    warnings: list[str] = []
    total: int = 0
    order_num: int = 0

def parse_llm(text: str) -> tuple:
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": MENU_PROMPT}, {"role": "user", "content": text}]
    )
    clean = r.choices[0].message.content.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    data = json.loads(clean)
    items_raw = data.get("items", [])
    item_names = [i.get("name", "").lower() for i in items_raw]
    unknown = [u for u in data.get("unknown", []) if not any(u.lower() in name for name in item_names)]
    return items_raw, unknown

def save_history(order_num, table, items, errors, total, text):
    path = os.path.join(os.path.dirname(__file__), "_orders.json")
    record = {"order_num": order_num, "table": table, "items": items, "errors": errors, "total": total, "time": datetime.now().isoformat(), "text": text}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []
    history.append(record)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def process_order(text: str, table: int = 0) -> dict:
    items_raw, unknown = parse_llm(text)
    items, errors, warnings = validate_order(items_raw, menu)
    for u in unknown:
        errors.append(f"'{u}' нет в меню")
    total = sum(i["price"] * i["quantity"] for i in items)
    order_num = next_order_num()
    print_order({"items": items, "errors": errors}, table=table, order_num=order_num)
    save_history(order_num, table, items, errors, total, text)
    return {"items": items, "errors": errors, "warnings": warnings, "total": total, "order_num": order_num}

@app.post("/order", response_model=OrderOut)
def create_order(req: OrderRequest):
    return process_order(req.text, req.table)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
    with open(path, encoding="utf-8") as f:
        return f.read()

@app.get("/history")
def get_history():
    path = os.path.join(os.path.dirname(__file__), "_orders.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)

@app.get("/menu-data")
def get_menu():
    return menu

@app.post("/stop-list")
def toggle_stop(body: dict):
    name = body.get("name", "")
    if name not in [i["name"] for i in menu["items"]]:
        raise HTTPException(400, "нет в меню")
    if name in menu["stop_list"]:
        menu["stop_list"].remove(name)
    else:
        menu["stop_list"].append(name)
    path = os.path.join(os.path.dirname(__file__), "menu.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(menu, f, ensure_ascii=False, indent=2)
    return {"stop_list": menu["stop_list"]}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
    tmp = os.path.join(os.path.dirname(__file__), f"_tmp_audio{ext}")
    with open(tmp, "wb") as f:
        f.write(await file.read())
    with open(tmp, "rb") as f:
        r = client.audio.transcriptions.create(
            file=(file.filename or "audio.wav", f.read()),
            model="whisper-large-v3-turbo",
            response_format="json"
        )
    os.remove(tmp)
    return {"text": r.text}

@app.post("/voice-order")
async def voice_order(file: UploadFile = File(...), table: int = 0):
    ext = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
    tmp = os.path.join(os.path.dirname(__file__), f"_tmp_audio{ext}")
    with open(tmp, "wb") as f:
        f.write(await file.read())
    with open(tmp, "rb") as f:
        r = client.audio.transcriptions.create(
            file=(file.filename or "audio.wav", f.read()),
            model="whisper-large-v3-turbo",
            response_format="json"
        )
    os.remove(tmp)
    text = r.text
    result = process_order(text, table)
    audio_path = tts(f"Заказ принят. {result['total']} рублей.")
    result["text"] = text
    result["audio_url"] = f"/audio/{os.path.basename(audio_path)}"
    return result

@app.get("/tts")
def text_to_speech(text: str = ""):
    path = tts(text or "пустой запрос")
    return FileResponse(path, media_type="audio/mpeg")
