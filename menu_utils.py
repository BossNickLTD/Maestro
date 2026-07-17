import json
import os

def load_menu():
    path = os.path.join(os.path.dirname(__file__), "menu.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def find_item(menu, name):
    name_lower = name.strip().lower()
    for item in menu["items"]:
        if item["name"].lower() == name_lower:
            return item

    alias = menu["aliases"].get(name_lower)
    if alias:
        for item in menu["items"]:
            if item["name"] == alias:
                return item

    return None

def validate_order(items_raw, menu):
    result = []
    errors = []

    for raw in items_raw:
        name = raw.get("name", "")
        qty = raw.get("quantity", 1)
        item = find_item(menu, name)

        if not item:
            errors.append(f"'{name}' нет в меню")
            continue
        if item["name"] in menu["stop_list"]:
            errors.append(f"{item['name']} закончился")
            continue

        result.append({"name": item["name"], "quantity": qty, "price": item["price"]})

    return result, errors
