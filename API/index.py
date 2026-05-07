import os
import json
import telebot
from fastapi import FastAPI, Request
from github import Github

# جلب الأسرار بطريقة صحيحة وآمنة
API_TOKEN = os.environ.get("BOT_TOKEN")
GH_TOKEN = os.environ.get("GH_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8294538151"))
REPO_NAME = os.environ.get("REPO_NAME")
CHANNEL_ID = "@zsewwi"

bot = telebot.TeleBot(API_TOKEN)
app = FastAPI()
gh = Github(GH_TOKEN)

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def get_db():
    repo = gh.get_repo(REPO_NAME)
    contents = repo.get_contents("db.json")
    return json.loads(contents.decoded_content.decode())

def update_db(data):
    repo = gh.get_repo(REPO_NAME)
    contents = repo.get_contents("db.json")
    repo.update_file(contents.path, "Update DB", json.dumps(data, indent=4), contents.sha)

# تم تغيير المسار هنا لتفادي مشكلة الروابط المكسورة
@app.post("/webhook")
async def process_update(request: Request):
    try:
        json_str = await request.body()
        update = telebot.types.Update.de_json(json_str.decode('utf-8'))
        bot.process_new_updates([update])
        return {"status": "ok"}
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error"}

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("اضغط هنا للاشتراك", url="https://t.me/zsewwi"))
        return bot.send_message(message.chat.id, "❌ يجب عليك الاشتراك في القناة أولاً لاستخدام البوت!", reply_markup=markup)

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn1 = telebot.types.InlineKeyboardButton("🎁 الأدوات المجانية", callback_data="free")
    btn2 = telebot.types.InlineKeyboardButton("💰 الأدوات المدفوعة", callback_data="paid")
    markup.add(btn1, btn2)
    
    if user_id == ADMIN_ID:
        markup.add(telebot.types.InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel"))

    bot.send_message(message.chat.id, "👋 أهلاً بك في متجر ستار للأدوات!", reply_markup=markup)

# ... (باقي دوال لوحة التحكم كما هي)

