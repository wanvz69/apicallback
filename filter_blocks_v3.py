import json
from collections import Counter

# ============================================================
# BLOCK FILTER V3 - STRICT
# ============================================================

INPUT = "items.json"
OUTPUT = "block_names.json"
DEBUG_OUTPUT = "block_filter_debug.json"

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

# Action types yang dari dataset lu paling kuat mengarah
# ke item yang bisa berada di world.
WORLD_ACTIONS = {
    17,  # normal block / foreground
    18,  # background
    19,  # seed/block related world item
}

# Action 20 dari data lu banyak berisi clothing/equipment.
# Jadi EXCLUDE total.
EXCLUDED_ACTIONS = {
    20,
}

# Editable type 4 dari sample lu = clothing/equipment.
EXCLUDED_EDITABLE = {
    4,
}

# Category yang terlihat aman untuk world item.
# Kita tidak hard-whitelist category karena beberapa block
# ternyata memakai category lain.
ALLOWED_CATEGORIES = {
    0,
    2,
    4,
    5,
    8,
    16,
    32,
    64,
    72,
    96,
    128,
    130,
    132,
    134,
}

# Collision yang masih masuk akal untuk tile.
ALLOWED_COLLISION = {
    0,
    1,
    2,
    3,
    4,
}

# ------------------------------------------------------------
# HARD NAME EXCLUDES
# ------------------------------------------------------------

EXCLUDED_NAME_WORDS = (
    # clothing
    "shirt",
    "pants",
    "shoes",
    "shoe",
    "hair",
    "hat",
    "cap",
    "skirt",
    "blouse",
    "bikini",
    "boxers",
    "thong",
    "tuxedo",
    "dress",
    "jacket",
    "coat",
    "glove",
    "socks",
    "sock",
    "mask",
    "face",
    "necklace",
    "earring",
    "wings",
    "wing",

    # equipment / weapon
    "sword",
    "pickaxe",
    "hammer",
    "wrench",
    "fist",
    "staff",
    "bow",
    "gun",
    "weapon",
    "shield",

    # pets
    "pet",
    "puppy",
    "kitten",

    # currencies / consumables / rewards
    "token",
    "ticket",
    "voucher",
    "coupon",
    "reward",

    # role / account / special
    "role",
    "permanent",

    # misc inventory objects that aren't normally tiles
    "seed",
)

# ------------------------------------------------------------
# HARD EXACT EXCLUDES
# ------------------------------------------------------------

EXCLUDED_EXACT_NAMES = {
    "",
    "blank",
    "blank seed",
    "fist",
    "wrench",
}

# ------------------------------------------------------------
# STRONG BLOCK NAME WORDS
# ------------------------------------------------------------

BLOCK_WORDS = (
    "block",
    "background",
    "wall",
    "brick",
    "platform",
    "wallpaper",
    "glass",
    "fence",
    "floor",
    "tile",
    "rock",
    "stone",
    "dirt",
    "grass",
    "sand",
    "lava",
    "wood",
    "tree",
    "bush",
    "flower",
    "mushroom",
    "spike",
    "ladder",
    "door",
    "window",
    "pillar",
    "column",
    "cloud",
    "crystal",
    "ore",
    "soil",
)

# ------------------------------------------------------------
# NAME PATTERNS THAT ARE USUALLY NOT WORLD BLOCKS
# ------------------------------------------------------------

NON_BLOCK_WORDS = (
    "clothing",
    "costume",
    "outfit",
    "accessory",
    "bundle",
    "pack",
    "box",
    "chest",
    "crate",
    "tool",
    "weapon",
    "sword",
    "pickaxe",
    "hammer",
    "shirt",
    "pants",
    "shoes",
    "hair",
    "hat",
    "cap",
    "wing",
    "wings",
    "pet",
    "egg",
    "seed",
)

# ============================================================
# HELPERS
# ============================================================

def normalize_name(value):
    return str(value or "").strip()


def contains_any(name, words):
    name = name.lower()

    for word in words:
        if word in name:
            return True

    return False


def is_seed(name):
    name = name.lower().strip()

    return (
        name.endswith(" seed")
        or " seed " in name
        or name.startswith("seed ")
    )


# ============================================================
# CLASSIFIER
# ============================================================

def classify(item):
    item_id = item.get("item_id")
    name = normalize_name(item.get("name"))

    editable = item.get("editable_type", -1)
    category = item.get("item_category", -1)
    action = item.get("action_type", -1)
    collision = item.get("collision_type", -1)

    score = 0
    reasons = []

    # ========================================================
    # HARD REJECT
    # ========================================================

    if not name:
        return False, -999, ["empty_name"]

    name_lower = name.lower()

    if name_lower in EXCLUDED_EXACT_NAMES:
        return False, -999, ["excluded_exact"]

    if is_seed(name):
        return False, -999, ["seed"]

    if action in EXCLUDED_ACTIONS:
        return False, -999, [f"excluded_action={action}"]

    if editable in EXCLUDED_EDITABLE:
        return False, -999, [f"excluded_editable={editable}"]

    if contains_any(name, EXCLUDED_NAME_WORDS):
        return False, -999, ["excluded_name"]

    # ========================================================
    # ACTION TYPE
    # ========================================================

    if action not in WORLD_ACTIONS:
        return False, -999, [f"not_world_action={action}"]

    if action == 17:
        score += 6
        reasons.append("action=17")

    elif action == 18:
        score += 6
        reasons.append("action=18")

    elif action == 19:
        score += 4
        reasons.append("action=19")

    # ========================================================
    # EDITABLE TYPE
    # ========================================================

    if editable == 0:
        score += 6
        reasons.append("editable=0")

    elif editable in (1, 2, 3):
        score += 2
        reasons.append(f"editable={editable}")

    else:
        # Unknown editable types are dangerous.
        score -= 5
        reasons.append(f"unknown_editable={editable}")

    # ========================================================
    # CATEGORY
    # ========================================================

    if category in ALLOWED_CATEGORIES:
        score += 3
        reasons.append(f"category={category}")

    else:
        score -= 4
        reasons.append(f"unknown_category={category}")

    # ========================================================
    # COLLISION
    # ========================================================

    if collision not in ALLOWED_COLLISION:
        return False, -999, [f"invalid_collision={collision}"]

    if collision == 1:
        score += 5
        reasons.append("collision=1")

    elif collision == 0:
        # Backgrounds can legitimately have no collision.
        if action == 18:
            score += 4
            reasons.append("background_collision=0")
        else:
            score += 1
            reasons.append("collision=0")

    elif collision in (2, 3, 4):
        score += 3
        reasons.append(f"collision={collision}")

    # ========================================================
    # NAME SIGNAL
    # ========================================================

    if contains_any(name, BLOCK_WORDS):
        score += 4
        reasons.append("block_name")

    else:
        # No block-like name.
        score -= 3
        reasons.append("no_block_name")

    # ========================================================
    # SPECIAL WORLD ITEM PATTERNS
    # ========================================================

    # Background items.
    if action == 18:
        score += 5
        reasons.append("background_action")

    # Normal foreground.
    if action == 17 and collision == 1:
        score += 4
        reasons.append("foreground_solid")

    # Some decorative world items have collision 0.
    if action == 17 and collision == 0:
        score += 1
        reasons.append("foreground_nonsolid")

    # ========================================================
    # FINAL DECISION
    # ========================================================

    # Very strict threshold.
    if score >= 17:
        return True, score, reasons

    return False, score, reasons


# ============================================================
# MAIN
# ============================================================

print("=" * 52)
print(" BLOCK FILTER V3 - STRICT")
print("=" * 52)

# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

items = data.get("items", [])

print(f"Original items : {len(items)}")

# ------------------------------------------------------------
# FILTER
# ------------------------------------------------------------

result = {}
debug = []

accepted = []
rejected = []

for item in items:

    item_id = item.get("item_id")
    name = normalize_name(item.get("name"))

    ok, score, reasons = classify(item)

    debug_entry = {
        "item_id": item_id,
        "name": name,
        "editable_type": item.get("editable_type"),
        "item_category": item.get("item_category"),
        "action_type": item.get("action_type"),
        "collision_type": item.get("collision_type"),
        "score": score,
        "accepted": ok,
        "reasons": reasons,
    }

    debug.append(debug_entry)

    if ok:
        result[str(item_id)] = name
        accepted.append(item)

    else:
        rejected.append(item)

# ------------------------------------------------------------
# SORT BY ITEM ID
# ------------------------------------------------------------

result = dict(
    sorted(
        result.items(),
        key=lambda x: int(x[0])
    )
)

# ------------------------------------------------------------
# SAVE MAIN JSON
# ------------------------------------------------------------

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )

# ------------------------------------------------------------
# SAVE DEBUG
# ------------------------------------------------------------

with open(DEBUG_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(
        debug,
        f,
        ensure_ascii=False,
        indent=2
    )

# ============================================================
# STATISTICS
# ============================================================

print(f"Filtered items : {len(result)}")
print(f"Rejected items : {len(rejected)}")
print(f"Output         : {OUTPUT}")
print(f"Debug          : {DEBUG_OUTPUT}")

print()
print("Accepted ACTION:")
for k, v in Counter(
    x.get("action_type")
    for x in accepted
).most_common():
    print(f"  {k:4} -> {v}")

print()
print("Accepted EDITABLE:")
for k, v in Counter(
    x.get("editable_type")
    for x in accepted
).most_common():
    print(f"  {k:4} -> {v}")

print()
print("Accepted CATEGORY:")
for k, v in Counter(
    x.get("item_category")
    for x in accepted
).most_common():
    print(f"  {k:4} -> {v}")

print()
print("Accepted COLLISION:")
for k, v in Counter(
    x.get("collision_type")
    for x in accepted
).most_common():
    print(f"  {k:4} -> {v}")

print()
print("=" * 52)
print("DONE")
print("=" * 52)
