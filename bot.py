from pyrogram import Client, filters
from pyrogram.enums import ParseMode
import json
import os
import uuid

# ------------- CONFIG ----------------

import os

API_ID = 36001520
API_HASH = "1dec0f6809024516068a0fbb92d6dc55"
BOT_TOKEN = "8028378886:AAFQj1E2H8CeeBEgFGkyCFlZoYeVLIL6UU4"

ADMIN_ID = 7945454951

DB_FILE = "messages.json"
# -------- DATABASE --------
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
# --------------------------


app = Client(
    "message_link_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# -------- USER START --------
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    parts = message.text.split(maxsplit=1)

    if len(parts) == 1:
        await message.reply("Send a valid message link.")
        return

    code = parts[1]
    db = load_db()

    if code not in db:
        await message.reply("Invalid or expired link.")
        return

    await client.send_message(
        chat_id=message.chat.id,
        text=db[code],
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False
    )
# -----------------------------


# -------- ADMIN SAVE --------
@app.on_message(filters.command("save") & filters.private)
async def save_command(client, message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("YOU ARE NOT PERMITTED TO USE THIS BOT.")
        return

    await message.reply("Send the message (text links supported).")
# ----------------------------


# -------- STORE MESSAGE --------
@app.on_message(filters.private & filters.text)
async def store_message(client, message):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text.startswith("/"):
        return

    db = load_db()
    code = str(uuid.uuid4())[:8]

    # ✅ STORE HTML VERSION
    db[code] = message.text.html

    save_db(db)

    bot_username = (await client.get_me()).username
    link = f"https://t.me/{bot_username}?start={code}"

    await message.reply(
        "Message saved successfully.\n\n"
        f"Link:\n{link}"
    )
# --------------------------------


print("Bot is running...")
app.run()






