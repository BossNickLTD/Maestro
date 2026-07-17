import os
from datetime import datetime

RECEIPTS_DIR = os.path.join(os.path.dirname(__file__), "receipts")

def print_order(order, table: int = 0, order_num: int = 0):
    os.makedirs(RECEIPTS_DIR, exist_ok=True)

    lines = []
    sep = "=" * 40
    dash = "-" * 40

    lines.append(sep)
    lines.append("            M A E S T R O")
    if order_num:
        lines.append(f"  заказ #{order_num} | Стол {table}" if table else f"  заказ #{order_num}")
    lines.append(f"  {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    lines.append(sep)

    for item in order.get("items", []):
        name = item.get("name", "")
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        total = qty * price
        mods = item.get("modifiers", {})
        mod_str = ""
        if mods:
            parts = [f"{k}: {v}" for k, v in mods.items()]
            mod_str = f" ({', '.join(parts)})"
        lines.append(f"  {name}{mod_str}")
        lines.append(f"    {qty} x {price} = {total}")

    lines.append(dash)
    total = sum(i.get("price", 0) * i.get("quantity", 1) for i in order.get("items", []))
    lines.append(f"  ИТОГО:                   {total}")
    lines.append(sep)
    lines.append("        Спасибо за заказ!")

    if order.get("errors"):
        lines.append(dash)
        for e in order["errors"]:
            lines.append(f"  ! {e}")

    lines.append(sep)
    lines.append("")

    text = "\n".join(lines)

    filename = f"order_{order_num or 0}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path = os.path.join(RECEIPTS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    try:
        print(f"[PRINTER] receipt saved: {path}")
    except:
        print("[PRINTER] receipt saved (file)")

    return path
