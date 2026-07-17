from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
import os
import json
from menu_utils import load_menu, validate_order, build_menu_prompt

app = FastAPI(title="Maestro API")

env_path = os.path.join(os.path.dirname(__file__), ".env")
with open(env_path) as f:
    for line in f:
        if line.startswith("GROQ_API_KEY="):
            os.environ["GROQ_API_KEY"] = line.strip().split("=", 1)[1]

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
menu = load_menu()

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

@app.post("/order", response_model=OrderOut)
def create_order(req: OrderRequest):
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MENU_PROMPT},
            {"role": "user", "content": req.text}
        ]
    )
    raw = r.choices[0].message.content

    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[-1]
        clean = clean.rsplit("```", 1)[0]
    clean = clean.strip()
    
    with open("_llm_raw.json", "w", encoding="utf-8") as f:
        f.write(clean)

    data = json.loads(clean)
    items_raw = data.get("items", [])
    item_names = [i.get("name", "").lower() for i in items_raw]
    unknown = [u for u in data.get("unknown", [])
               if not any(u.lower() in name for name in item_names)]
    items, errors, warnings = validate_order(items_raw, menu)
    for u in unknown:
        errors.append(f"'{u}' нет в меню")
    total = sum(i["price"] * i["quantity"] for i in items)
    return {"items": items, "errors": errors, "warnings": warnings, "total": total}
