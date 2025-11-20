import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from fastapi import FastAPI, Request
import uvicorn

TOKEN = os.getenv("TOKEN")   # Render environment variable
DATA_FILE = "referrals.json"

# Load referrals
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

# Save referrals
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)

    data = load_data()
    if user_id not in data:
        data[user_id] = {"count": 0}
        save_data(data)

    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"

    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n"
        f"Here is your referral link:\n{referral_link}\n\n"
        f"Share this link!"
    )

# Track referrals
async def track_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)

    if context.args:
        referrer_id = context.args[0]

        if referrer_id != user_id:
            data = load_data()
            if referrer_id in data:
                data[referrer_id]["count"] += 1
                save_data(data)

                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 Someone joined using your link!\n"
                         f"Total referrals: {data[referrer_id]['count']}"
                )

    await update.message.reply_text("You joined successfully!")

# Leaderboard
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()

    if not data:
        await update.message.reply_text("No referral data yet.")
        return

    sorted_users = sorted(data.items(), key=lambda x: x[1]["count"], reverse=True)

    msg = "🏆 *Referral Leaderboard* 🏆\n\n"
    rank = 1
    for user_id, info in sorted_users:
        try:
            chat = await context.bot.get_chat(int(user_id))
            name = chat.first_name
        except:
            name = "Unknown User"

        msg += f"{rank}. {name} — {info['count']} referrals\n"
        rank += 1

    await update.message.reply_text(msg)

# FASTAPI WEB SERVER
app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    await application.update_queue.put(Update.de_json(body, application.bot))
    return {"ok": True}

@app.get("/")
def home():
    return {"status": "Bot is running via webhook!"}

# MAIN ENTRYPOINT
if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", track_referral))
    application.add_handler(CommandHandler("leaderboard", leaderboard))

    # Start webhook
    port = int(os.getenv("PORT", 10000))
    app_url = os.getenv("RENDER_EXTERNAL_URL")

    # Set Telegram webhook
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        application.bot.set_webhook(f"{app_url}/webhook")
    )

    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=port)
