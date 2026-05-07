import os
import telebot
from flask import Flask, request

# جلب التوكن من الإعدادات
API_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(API_TOKEN, threaded=False)
app = Flask(__name__)

# المسار الرئيسي لاستقبال التحديثات
@app.route('/', methods=['POST'])
def receive_update():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return '403'

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "🔱 تم الاتصال بنجاح! متجر القيصر جاهز للعمل.")

# هذا السطر هو مفتاح الحل لفيرسل
def handler(request):
    return app(request)

