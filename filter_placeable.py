import json
import re

INPUT = "items.json"
OUTPUT = "placeable_names.json"
DEBUG_OUTPUT = "placeable_debug.json"

LOCK_PATTERNS = (
    r"\block\b",
    r"\blocked\b",
)

NON_PLACEABLE_PATTERNS = (
    r"\bseed\b",
    r"\bshirt\b",
    r"\bpants\b",
    r"\bshoes\b",
    r"\bhair\b",
    r"\bhat\b",
    r"\bcap\b",
    r"\bskirt\b",
    r"\bdress\b",
    r"\bbikini\b",
    r"\bthong\b",
    r"\bboxers\b",
    r"\bglove\b",
    r"\bsword\b",
    r"\bpickaxe\b",
    r"\bwrench\b",
    r"\bfist\b",
    r"\bwing\b",
    r"\bwings\b",
    r"\bnecklace\b",
    r"\bmask\b",
    r"\bhelmet\b",
    r"\barmor\b",
    r"\bcape\b",
    r"\bbackpack\b",
    r"\bweapon\b",
    r"\bpet\b",
    r"\bnull_item\b",
)

def normalize_name(name):
    name = str(name or "").lower()
    name = re.sub(r"`.", "", name)
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return " ".join(name.split())


def matches_any(text, patterns):
    return any(re.search(pattern, text) for pattern in patterns)


def evaluate(item):
    name_raw = str(item.get("name", "")).strip()
    name = normalize_name(name_raw)

    editable = item.get("editable_type", -1)
    category = item.get("item_category", -1)
    action = item.get("action_type", -1)
    collision = item.get("collision_type", -1)
    item_kind = item.get("item_kind", -1)

    score = 0
    reasons = []

    if not name:
        return False, -999, ["empty_name"]

    if matches_any(name, LOCK_PATTERNS):
        return False, -999, ["lock_item"]

    if matches_any(name, NON_PLACEABLE_PATTERNS):
        return False, -999, ["non_placeable_name"]

    # =========================================================
    # EDITABLE TYPE
    # =========================================================

    # 0 merupakan pola yang sangat umum pada world/placeable item.
    if editable == 0:
        score += 6
        reasons.append("editable=0")

    # Beberapa item placeable bisa memakai tipe editable lain.
    elif editable in (1, 2, 3):
        score += 2
        reasons.append(f"editable={editable}")

    # Apparel / wearable biasanya editable 4.
    elif editable == 4:
        score -= 8
        reasons.append("editable=4")

    # =========================================================
    # ACTION TYPE
    # =========================================================

    # Dari dataset yang sudah kita cek:
    # 17 = pola kuat untuk block/foreground
    # 18 = pola kuat untuk background
    # 19 = banyak item world/placeable
    if action == 17:
        score += 7
        reasons.append("action=17")

    elif action == 18:
        score += 7
        reasons.append("action=18")

    elif action == 19:
        score += 5
        reasons.append("action=19")

    elif action in (14, 15, 16, 20):
        score += 1
        reasons.append(f"action={action}")

    else:
        score -= 3
        reasons.append(f"other_action={action}")

    # =========================================================
    # COLLISION
    # =========================================================

    if collision == 1:
        score += 3
        reasons.append("collision=1")

    elif collision == 0:
        score += 2
        reasons.append("collision=0")

    elif collision in (2, 3, 4):
        score += 1
        reasons.append(f"collision={collision}")

    else:
        score -= 2
        reasons.append(f"unknown_collision={collision}")

    # =========================================================
    # CATEGORY
    # =========================================================

    # Category 0 sangat dominan pada item world dari dataset lu.
    if category == 0:
        score += 3
        reasons.append("category=0")

    elif category in (1, 2, 3, 4, 5, 8, 16, 32, 64, 72, 96, 128):
        score += 1
        reasons.append(f"category={category}")

    # =========================================================
    # ITEM KIND
    # =========================================================

    if item_kind == 0:
        score += 1
        reasons.append("item_kind=0")

    # =========================================================
    # FINAL DECISION
    # =========================================================

    # Strong placeable patterns.
    strong_pattern = (
        action in (17, 18)
        and editable in (0, 1, 2, 3)
    )

    foreground_pattern = (
        action == 17
        and collision in (0, 1, 2, 3, 4)
    )

    background_pattern = (
        action == 18
        and editable in (0, 1, 2, 3)
    )

    # Action 19 perlu lebih hati-hati karena dataset
    # juga memiliki item non-world dengan action 19.
    action19_pattern = (
        action == 19
        and editable in (0, 1, 2, 3)
        and category == 0
        and collision in (0, 1, 2, 3, 4)
    )

    if strong_pattern:
        reasons.append("strong_placeable_pattern")
        return True, score, reasons

    if foreground_pattern:
        reasons.append("foreground_pattern")
        return True, score, reasons

    if background_pattern:
        reasons.append("background_pattern")
        return True, score, reasons

    if action19_pattern and score >= 10:
        reasons.append("action19_placeable_pattern")
        return True, score, reasons

    return False, score, reasons


def main():
    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])

    result = {}
    debug = []

    for item in items:
        item_id = item.get("item_id")
        name = str(item.get("name", "")).strip()

        accepted, score, reasons = evaluate(item)

        debug.append({
            "item_id": item_id,
            "name": name,
            "accepted": accepted,
            "score": score,
            "editable_type": item.get("editable_type"),
            "item_category": item.get("item_category"),
            "action_type": item.get("action_type"),
            "collision_type": item.get("collision_type"),
            "item_kind": item.get("item_kind"),
            "reasons": reasons,
        })

        if accepted and item_id is not None:
            result[str(item_id)] = name

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    with open(DEBUG_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            debug,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("====================================")
    print(" PLACEABLE FILTER")
    print("====================================")
    print(f"Original items : {len(items)}")
    print(f"Placeable      : {len(result)}")
    print(f"Output         : {OUTPUT}")
    print(f"Debug          : {DEBUG_OUTPUT}")
    print("====================================")


if __name__ == "__main__":
    main()
