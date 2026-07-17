import json
import os
from difflib import SequenceMatcher

def load_menu():
    path = os.path.join(os.path.dirname(__file__), "menu.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_menu_prompt(menu):
    lines = []
    for item in menu["items"]:
        mods = menu["modifiers"].get(item["name"], {})
        mod_str = ""
        if mods:
            opts = "; ".join(f"{k}: {', '.join(v)}" for k, v in mods.items())
            mod_str = f" [модификаторы: {opts}]"
        lines.append(f"  - {item['name']} ({item['price']} руб){mod_str}")
    return "\n".join(lines)

def fuzzy_match(name, candidates):
    best, best_score = None, 0
    for c in candidates:
        score = SequenceMatcher(None, name.lower(), c.lower()).ratio()
        if score > best_score:
            best_score, best = score, c
    return best if best_score > 0.6 else None

def find_item(menu, name):
    name_lower = name.strip().lower()

    for item in menu["items"]:
        if item["name"].lower() == name_lower:
            return item, None

    alias = menu["aliases"].get(name_lower)
    if alias:
        for item in menu["items"]:
            if item["name"] == alias:
                return item, None

    names = [item["name"] for item in menu["items"]]
    fuzzy = fuzzy_match(name_lower, names)
    if fuzzy:
        for item in menu["items"]:
            if item["name"] == fuzzy:
                return item, f"показалось: '{name}' → '{fuzzy}'"

    for item in menu["items"]:
        item_words = set(item["name"].lower().split())
        name_words = set(name_lower.split())
        common = name_words & item_words
        if common and len(common) / max(len(item_words), len(name_words)) > 0.4:
            return item, f"угадано: '{name}' → '{item['name']}'"

    return None, None

def extract_modifiers(item_name, menu):
    mods = menu["modifiers"].get(item_name, {})
    return {k: v[0] for k, v in mods.items()}

def validate_order(items_raw, menu):
    result = []
    errors = []
    warnings = []

    for raw in items_raw:
        name = raw.get("name", "")
        qty = raw.get("quantity", 1)

        item, warn = find_item(menu, name)
        if warn:
            warnings.append(warn)

        if not item:
            errors.append(f"'{name}' нет в меню")
            continue
        if item["name"] in menu.get("stop_list", []):
            errors.append(f"{item['name']} закончился")
            continue

        mods = raw.get("modifiers", raw.get("modifications", {}))
        result.append({
            "name": item["name"],
            "quantity": qty,
            "price": item["price"],
            "modifiers": mods
        })

    return result, errors, warnings
