import os
from groq import Groq

api_key = input("Ключ: ")
client = Groq(api_key=api_key)

user_text = "Принесите два латте и круассан"

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "Извлеки заказ из сообщения. Ответь ТОЛЬКО JSON. Формат: {\"items\": [{\"name\": \"...\", \"quantity\": число}]}"},
        {"role": "user", "content": user_text}
    ]
)

print(response.choices[0].message.content)