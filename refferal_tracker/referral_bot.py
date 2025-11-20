import json
import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
from telegram.error import BadRequest
import uvicorn

# Read token from Render environment
TOKEN = os.environ.get("BOT_TOKEN")

DATA_FILE = "referrals.json"

# ---------------- JSON STORAGE ----------------
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ------------- TELEGRAM BOT COMMANDS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles normal start + referral tracking"""
    user = update.effective_user
    user_id = str(user.id)

    data = load_data()

    # Create user entry if not exists
    if user_id not in data:
        data[user_id] = {"count": 0}
        save_data(data)

    # ---------- REFERRAL TRACKING ----------
    if context.args:
        referrer_id = context.args[0]

        if referrer_id != user_id and referrer_id in data:
            data[referrer_id]["count"] += 1
            save_data(data)

            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"🎉 Someone joined using your referral link!\n"
                     f"Total referrals: {data[referrer_id]['count']}"
            )

        await update.message.reply_text("You joined successfully!")
        return

    # ---------- NORMAL /start ----------
    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"

    await update.message.reply_text(
        f"👋 Hello {user.first_name}!\n"
        f"Here is your referral link:\n"
        f"{referral_link}\n\n"
        f"Share this link – anyone who joins using it will be counted under you!"
    )

async def myreferrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user’s referral count"""
    user_id = str(update.effective_user.id)
    data = load_data()

    count = data.get(user_id, {}).get("count", 0)

    await update.message.reply_text(
        f"📊 You have {count} total referrals."
    )

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the leaderboard"""
    data = load_data()

    if not data:
        await update.message.reply_text("😕 No referral data yet.")
        return

    sorted_users = sorted(data.items(), key=lambda x: x[1]["count"], reverse=True)

    msg = "🏆 *Referral Leaderboard* 🏆\n\n"
    rank = 1

    for user_id, info in sorted_users:
        try:
            chat = await context.bot.get_chat(int(user_id))
            name = chat.first_name
        except BadRequest:
            name = "Unknown User"

        msg += f"{rank}. {name} — {info['count']} referrals\n"
        rank += 1

    await update.message.reply_text(msg)

# ---------------- FASTAPI DASHBOARD ----------------

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return "<h2>Bot is running successfully! 🚀</h2>"

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    data = load_data()

    total_users = len(data)
    total_referrals = sum(v["count"] for v in data.values())

    sorted_users = sorted(data.items(), key=lambda x: x[1]["count"], reverse=True)

    leaderboard_html = ""
    rank = 1
    for user_id, info in sorted_users:
        leaderboard_html += f"""
        <tr>
            <td>{rank}</td>
            <td>{user_id}</td>
            <td>{info['count']}</td>
        </tr>
        """
        rank += 1

    html = f"""
    <html>
    <head>
        <title>Referral Dashboard</title>
        <style>
            body {{
                font-family: Arial;
                padding: 20px;
                background-color: #f4f4f4;
            }}
            .box {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
                text-align: center;
            }}
            th {{
                background-color: #222;
                color: white;
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>📊 Referral Dashboard</h1>

            <p><b>Total Users:</b> {total_users}</p>
            <p><b>Total Referrals:</b> {total_referrals}</p>

            <h2>🏆 Leaderboard</h2>
            <table>
                <tr>
                    <th>Rank</th>
                    <th>User ID</th>
                    <th>Referrals</th>
                </tr>
                {leaderboard_html}
            </table>
        </div>
    </body>
    </html>
    """

    return html

# --------------- START BOT + API TOGETHER -------------------
async def run_bot():
    app_telegram = ApplicationBuilder().token(TOKEN).build()

    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("myreferrals", myreferrals))
    app_telegram.add_handler(CommandHandler("leaderboard", leaderboard))

    print("Telegram bot started...")
    await app_telegram.initialize()

    # IMPORTANT: Remove webhook (Telegram prefers webhook by default)
    await app_telegram.bot.delete_webhook(drop_pending_updates=True)

    await app_telegram.start()
    await app_telegram.updater.start_polling()
    await app_telegram.updater.idle()


def main():
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

if __name__ == "__main__":
    main()
