from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
import os
import json

app = FastAPI(title="Maestro API")

env_path = os.path.join(os.path.dirname(__file__), ".env")
with open(env_path) as f:
    for line in f:
        if line.startswith("GROQ_API_KEY="):
            os.environ["GROQ_API_KEY"] = line.strip().split("=", 1)[1]

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class OrderRequest(BaseModel):
    text: str

class Item(BaseModel):
    name: str
    quantity: int

class OrderResponse(BaseModel):
    items: list[Item]

@app.post("/order", response_model=OrderResponse)
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
    return OrderResponse(items=data["items"])
