import os
import json
import telebot
from fastapi import FastAPI, Request
from github import Github

# جلب الإعدادات من Vercel Environment Variables
API_TOKEN = "8788224553:AAHsmR3J0AmDCAvjycduCUNDZF0C5pV3468"
ADMIN_ID = 8294538151
# تأكد من إضافة GH_TOKEN و REPO_NAME في إعدادات Vercel
GH_TOKEN = os.environ.get("GH_TOKEN")
REPO_NAME = os.environ.get("REPO_NAME") 

bot = telebot.TeleBot(API_TOKEN, threaded=False)
app = FastAPI()

# مسار استقبال التحديثات من تلجرام
@app.post("/api")
async def handle_webhook(request: Request):
    update = telebot.types.Update.de_json(await request.json())
    bot.process_new_updates([update])
    return {"status": "ok"}

@app.get("/api")
async def check():
    return {"message": "System Online"}

@bot.message_handler(commands=['start'])
def send_welcome(m):
    # نظام الاشتراك الإجباري
    try:
        status = bot.get_chat_member("@zsewwi", m.from_user.id).status
        if status not in ['member', 'administrator', 'creator']:
            return bot.reply_to(m, "❌ اشترك في القناة أولاً: @zsewwi")
    except: pass

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📱 متجر الأرقام", callback_data="nums"))
    markup.add(telebot.types.InlineKeyboardButton("🛠️ الأدوات", callback_data="tools"))
    
    if m.from_user.id == ADMIN_ID:
        markup.add(telebot.types.InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin"))
        
    bot.send_message(m.chat.id, "🔱 مرحباً بك في متجر القيصر المتكامل", reply_markup=markup)

# أضف هنا باقي معالجات الأزرار (callback_query_handler)

