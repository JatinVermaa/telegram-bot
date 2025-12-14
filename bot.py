from pyrogram import Client, filters
from pyrogram.enums import ParseMode
import json
import os
import uuid

# ------------- CONFIG ----------------
API_ID = 35341018
API_HASH = "c98e5177a3e1d3df757bd53816566303"
BOT_TOKEN = "8377620232:AAEHHQ_PRTMKwFmxPXR8ZAT3_6_b9sYEZ1I"

ADMIN_ID = 8419089180
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
