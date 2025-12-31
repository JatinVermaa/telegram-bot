from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import json, os, uuid

# ================= CONFIG =================
API_ID = 33850142
API_HASH = "56f42eeb58a6d062a54e432b12713e25"
BOT_TOKEN = "8490541677:AAH0SdxEySzpQuYbtNIamK9eexwd-Ih1ZKM"

OWNER_ID = 8586483676
ADMIN_IDS = {8586483676}

SESSION_NAME = "adv_msg_bot"
DB_FILE = "db.json"

# =========================================

STATE = {}

# ================= DB =================
def load_db():
    if not os.path.exists(DB_FILE):
        return {"messages": {}, "fixed_message": None}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
# =====================================

def is_admin(uid):
    return uid == OWNER_ID or uid in ADMIN_IDS

# ================= BUTTON PARSER =================
def parse_buttons(text):
    rows = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        row = []
        for part in raw.split("&&"):
            part = part.strip().replace("–", "-").replace("—", "-")

            if "-" in part:
                title, value = part.split("-", 1)
            else:
                title = value = part

            title = title.strip()
            value = value.strip()

            if value.startswith("popup:"):
                row.append(("popup", title, value[6:]))
            elif value.startswith("alert:"):
                row.append(("alert", title, value[6:]))
            elif value.startswith("copy:"):
                row.append(("copy", title, value[5:]))
            elif value.startswith("share:"):
                row.append(("share", title, value[6:]))
            elif value == "rules":
                row.append(("rules", title, ""))
            else:
                if value.startswith("t.me/"):
                    value = "https://" + value
                row.append(("url", title, value))

        rows.append(row)
    return rows

def build_keyboard(rows):
    kb = []
    for row in rows:
        btns = []
        for t, txt, val in row:
            if t == "url":
                btns.append(InlineKeyboardButton(txt, url=val))
            else:
                btns.append(InlineKeyboardButton(txt, callback_data=f"{t}|{val}"))
        kb.append(btns)
    return InlineKeyboardMarkup(kb) if kb else None
# ===============================================

app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= START =================
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    db = load_db()
    uid = message.from_user.id
    args = message.text.split(maxsplit=1)

    if len(args) == 2:
        code = args[1]
        entry = db["messages"].get(code)
        if not entry:
            await message.reply("❌ Invalid or expired link")
            return

        # 🔥 MERGED MESSAGE
        if entry["type"] == "merged":
            for c in entry["items"]:
                msg = db["messages"].get(c)
                if not msg:
                    continue
                kb = build_keyboard(msg["buttons"])
                if msg["image"]:
                    await message.reply_photo(msg["image"], caption=msg["text"], reply_markup=kb)
                else:
                    await message.reply(msg["text"], reply_markup=kb)
            return

        # 🔹 SINGLE MESSAGE
        kb = build_keyboard(entry["buttons"])
        if entry["image"]:
            await message.reply_photo(entry["image"], caption=entry["text"], reply_markup=kb)
        else:
            await message.reply(entry["text"], reply_markup=kb)
        return

    if is_admin(uid):
        await admin_panel(message)
    else:
        fixed = db.get("fixed_message")
        if fixed:
            kb = build_keyboard(fixed["buttons"])
            if fixed["image"]:
                await message.reply_photo(fixed["image"], caption=fixed["text"], reply_markup=kb)
            else:
                await message.reply(fixed["text"], reply_markup=kb)
        else:
            await message.reply("Welcome 👋")

# ================= ADMIN PANEL =================
async def admin_panel(message):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Save Message", callback_data="save")],
        [InlineKeyboardButton("➕ Add Buttons", callback_data="buttons")],
        [InlineKeyboardButton("➕ Add Message", callback_data="merge")],
        [InlineKeyboardButton("🧷 Fix Message", callback_data="fix")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])
    await message.reply("⚙️ Admin Panel", reply_markup=kb)

# ================= CALLBACKS =================
@app.on_callback_query()
async def callbacks(client, cb):
    uid = cb.from_user.id
    if not is_admin(uid):
        return

    STATE[uid] = {}

    if cb.data == "cancel":
        STATE.pop(uid, None)
        await cb.message.edit("❌ Cancelled")
        return

    if cb.data == "merge":
        STATE[uid]["step"] = "merge_codes"
        await cb.message.edit("🔗 Send message codes to merge (one per line)")
        return

    if cb.data == "save":
        STATE[uid]["step"] = "text"
        await cb.message.edit("✏️ Send message text")
        return

    if cb.data == "buttons":
        STATE[uid]["step"] = "btn_code"
        await cb.message.edit("🔑 Send message code")
        return

    if cb.data == "fix":
        STATE[uid]["step"] = "fix_text"
        await cb.message.edit("✏️ Send fixed message text")

# ================= TEXT HANDLER =================
@app.on_message(filters.private)
async def admin_flow(client, message):
    uid = message.from_user.id
    if uid not in STATE:
        return

    db = load_db()
    state = STATE[uid]

    # 🔥 MERGE MESSAGES
    if state.get("step") == "merge_codes":
        codes = [c.strip() for c in message.text.splitlines() if c.strip()]
        for c in codes:
            if c not in db["messages"]:
                await message.reply(f"❌ Invalid code: {c}")
                return

        new_code = str(uuid.uuid4())[:8]
        db["messages"][new_code] = {
            "type": "merged",
            "items": codes
        }
        save_db(db)
        STATE.pop(uid)

        bot = await client.get_me()
        await message.reply(
            f"✅ Messages merged successfully\n\n"
            f"https://t.me/{bot.username}?start={new_code}"
        )
        return

    # SAVE MESSAGE
    if state.get("step") == "text":
        state["text"] = message.text
        state["step"] = "image"
        await message.reply("🖼 Send image or type skip")
        return

    if state.get("step") == "image":
        code = str(uuid.uuid4())[:8]
        db["messages"][code] = {
            "type": "single",
            "text": state["text"],
            "image": message.photo.file_id if message.photo else None,
            "buttons": []
        }
        save_db(db)
        STATE.pop(uid)
        bot = await client.get_me()
        await message.reply(f"✅ Saved\nhttps://t.me/{bot.username}?start={code}")
        return

    # ADD BUTTONS
    if state.get("step") == "btn_code":
        state["code"] = message.text.strip()
        state["step"] = "btn_text"
        await message.reply("📎 Send button structure")
        return

    if state.get("step") == "btn_text":
        code = state["code"]
        db["messages"][code]["buttons"] = parse_buttons(message.text)
        save_db(db)
        STATE.pop(uid)
        await message.reply("✅ Buttons added")

# ================= CALLBACK BUTTON ACTIONS =================
@app.on_callback_query(filters.regex("^(popup|alert|copy|share|rules)"))
async def button_actions(client, cb):
    action, data = cb.data.split("|", 1)
    await cb.answer(data, show_alert=(action in {"alert", "copy", "rules"}))

print("🚀 Bot is running...")
app.run()





