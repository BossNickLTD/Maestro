from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
import os
import json
from menu_utils import load_menu, validate_order

app = FastAPI(title="Maestro API")

env_path = os.path.join(os.path.dirname(__file__), ".env")
with open(env_path) as f:
    for line in f:
        if line.startswith("GROQ_API_KEY="):
            os.environ["GROQ_API_KEY"] = line.strip().split("=", 1)[1]

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
menu = load_menu()

class OrderRequest(BaseModel):
    text: str

class Item(BaseModel):
    name: str
    quantity: int
    price: int = 0

class OrderResponse(BaseModel):
    items: list[Item]
    errors: list[str] = []

@app.post("/order")
def create_order(req: OrderRequest):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Ты — AI-официант. Извлеки заказ из сообщения гостя. Ответь ТОЛЬКО JSON без пояснений. Формат: {\"items\": [{\"name\": \"...\", \"quantity\": число}]}"},
            {"role": "user", "content": req.text}
        ]
    )
    raw = response.choices[0].message.content
    data = json.loads(raw)
    items, errors = validate_order(data["items"], menu)
    return {"items": items, "errors": errors, "total": sum(i["price"] * i["quantity"] for i in items)}
