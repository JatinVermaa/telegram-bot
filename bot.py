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

    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue

        row = []
        parts = raw_line.split("&&")

        for part in parts:
            part = part.strip()

            # Normalize weird dashes
            part = part.replace("–", "-").replace("—", "-")

            title = None
            value = None

            if "-" in part:
                title, value = part.split("-", 1)
                title = title.strip()
                value = value.strip()
            else:
                # 🔥 ALLOW LINK-ONLY BUTTONS
                value = part.strip()
                title = value.replace("https://", "").replace("http://", "")

            if not value:
                continue

            # -------- SPECIAL BUTTONS --------
            if value.startswith("popup:"):
                row.append({"type": "popup", "text": title, "data": value[6:].strip()})

            elif value.startswith("alert:"):
                row.append({"type": "alert", "text": title, "data": value[6:].strip()})

            elif value.startswith("copy:"):
                row.append({"type": "copy", "text": title, "data": value[5:].strip()})

            elif value.startswith("share:"):
                row.append({"type": "share", "text": title, "data": value[6:].strip()})

            elif value == "rules":
                row.append({"type": "rules", "text": title, "data": ""})

            else:
                # 🔥 FORCE VALID URL
                if value.startswith("t.me/"):
                    value = "https://" + value

                row.append({"type": "url", "text": title, "data": value})

        if row:
            rows.append(row)

    return rows
def build_keyboard(rows):
    kb = []
    for row in rows:
        btn_row = []
        for b in row:
            if b["type"] == "url":
                btn_row.append(InlineKeyboardButton(b["text"], url=b["data"]))
            else:
                btn_row.append(
                    InlineKeyboardButton(
                        b["text"],
                        callback_data=f"{b['type']}|{b['data']}"
                    )
                )
        kb.append(btn_row)
    return InlineKeyboardMarkup(kb) if kb else None
# ===============================================

app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= START =================
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    db = load_db()
    uid = message.from_user.id
    args = message.text.split(maxsplit=1)

    # Message link access
    if len(args) == 2:
        code = args[1]
        msg = db["messages"].get(code)
        if not msg:
            await message.reply("❌ Invalid or expired link")
            return
        kb = build_keyboard(msg["buttons"])
        if msg["image"]:
            await message.reply_photo(msg["image"], caption=msg["text"], reply_markup=kb)
        else:
            await message.reply(msg["text"], reply_markup=kb)
        return

    # Admin auto panel
    if is_admin(uid):
        await admin_panel(client, message)
        return

    # Normal user fixed message
    fixed = db.get("fixed_message")
    if fixed:
        kb = build_keyboard(fixed["buttons"])
        if fixed["image"]:
            await message.reply_photo(fixed["image"], caption=fixed["text"], reply_markup=kb)
        else:
            await message.reply(fixed["text"], reply_markup=kb)
    else:
        await message.reply("Welcome 👋")
# =========================================

# ================= ADMIN PANEL =================
async def admin_panel(client, message):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Save Message", callback_data="save")],
        [InlineKeyboardButton("➕ Add Buttons", callback_data="buttons")],
        [InlineKeyboardButton("🧷 Fix Message", callback_data="fix")],
        [InlineKeyboardButton("👁 Preview", callback_data="preview")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])
    await message.reply("⚙️ Admin Panel", reply_markup=kb)
# ===============================================

# ================= CALLBACKS =================
@app.on_callback_query()
async def callbacks(client, cb):
    uid = cb.from_user.id
    if not is_admin(uid):
        return

    STATE[uid] = STATE.get(uid, {})

    if cb.data == "cancel":
        STATE.pop(uid, None)
        await cb.message.edit("❌ Cancelled")
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
        return

    if cb.data == "preview":
        STATE[uid]["step"] = "preview"
        await cb.message.edit("🔑 Send message code")
# ===============================================

# ================= TEXT HANDLER =================
@app.on_message(filters.private)
async def admin_flow(client, message):
    uid = message.from_user.id
    if not is_admin(uid) or uid not in STATE:
        return

    db = load_db()
    state = STATE[uid]

    # SAVE MESSAGE
    if state.get("step") == "text":
        state["text"] = message.text
        state["step"] = "image"
        await message.reply("🖼 Send image or type skip")
        return

    if state.get("step") == "image":
        code = str(uuid.uuid4())[:8]
        db["messages"][code] = {
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
        await message.reply("Send button structure")
        return

    if state.get("step") == "btn_text":
        code = state["code"]
        if code not in db["messages"]:
            await message.reply("❌ Invalid code")
            return
        db["messages"][code]["buttons"] = parse_buttons(message.text)
        save_db(db)
        STATE.pop(uid)
        await message.reply("✅ Buttons set successfully")
        return

    # FIX MESSAGE
    if state.get("step") == "fix_text":
        state["text"] = message.text
        state["step"] = "fix_image"
        await message.reply("🖼 Send image or type skip")
        return

    if state.get("step") == "fix_image":
        db["fixed_message"] = {
            "text": state["text"],
            "image": message.photo.file_id if message.photo else None,
            "buttons": []
        }
        save_db(db)
        STATE.pop(uid)
        await message.reply("📌 Fixed message saved")
        return

    # PREVIEW
    if state.get("step") == "preview":
        code = message.text.strip()
        msg = db["messages"].get(code)
        if not msg:
            await message.reply("❌ Invalid code")
            return
        kb = build_keyboard(msg["buttons"])
        if msg["image"]:
            await message.reply_photo(msg["image"], caption=msg["text"], reply_markup=kb)
        else:
            await message.reply(msg["text"], reply_markup=kb)
        STATE.pop(uid)
# ===============================================

# ================= CALLBACK BUTTON ACTIONS =================
@app.on_callback_query(filters.regex("^(popup|alert|copy|share|rules)"))
async def button_actions(client, cb):
    action, data = cb.data.split("|", 1)

    if action == "popup":
        await cb.answer(data, show_alert=False)
    elif action == "alert":
        await cb.answer(data, show_alert=True)
    elif action == "copy":
        await cb.answer(f"Copied:\n{data}", show_alert=True)
    elif action == "share":
        await cb.answer("Use share button", show_alert=False)
    elif action == "rules":
        await cb.answer("📜 Group rules here", show_alert=True)
# ===============================================

print("🚀 Bot is running...")
app.run()



