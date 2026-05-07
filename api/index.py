import os
import telebot
from flask import Flask, request

# الإعدادات
API_TOKEN = os.environ.get("BOT_TOKEN")
# استخدام Flask بدلاً من FastAPI لأنه أكثر استقراراً مع توجيهات Vercel البسيطة
app = Flask(__name__)
bot = telebot.TeleBot(API_TOKEN, threaded=False)

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return '403'

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "🔱 تم كسر الصمت! متجر القيصر يعمل الآن 100%")

@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    # منطق الأزرار هنا
    pass

# هذا السطر ضروري لـ Vercel
def handler(request):
    return app(request)

