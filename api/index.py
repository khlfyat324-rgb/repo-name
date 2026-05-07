import os
import json
import base64
import requests
import telebot
from flask import Flask, request

# --- [ الإعدادات من Environment Variables ] ---
TOKEN = os.environ.get("BOT_TOKEN") #
GH_TOKEN = os.environ.get("GH_TOKEN")
REPO = os.environ.get("REPO_NAME") # صيغة: username/repo
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8294538151"))
CHANNEL = "@zsewwi"

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- [ وظائف التعامل مع GitHub API - قاعدة البيانات والملفات ] ---
def gh_io(path, method="GET", content=None, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    if method == "GET":
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            return json.loads(base64.b64decode(data['content']).decode('utf-8')), data['sha']
        return {}, None
    
    elif method == "PUT":
        payload = {
            "message": "Update Data",
            "content": base64.b64encode(json.dumps(content, indent=4).encode('utf-8')).decode('utf-8'),
            "sha": sha
        }
        return requests.put(url, headers=headers, json=payload).status_code
    
    elif method == "DELETE":
        payload = {"message": "Delete File", "sha": sha}
        return requests.delete(url, headers=headers, json=payload).status_code

# --- [ التحقق من الاشتراك ] ---
def is_sub(uid):
    try:
        s = bot.get_chat_member(CHANNEL, uid).status
        return s in ['member', 'administrator', 'creator']
    except: return False

# --- [ لوحات التحكم ] ---
def main_markup(uid):
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    m.add(
        telebot.types.InlineKeyboardButton("📱 الأرقام", callback_data="view_nums"),
        telebot.types.InlineKeyboardButton("💰 أدوات مدفوعة", callback_data="view_paid"),
        telebot.types.InlineKeyboardButton("🎁 أدوات مجانية", callback_data="view_free"),
        telebot.types.InlineKeyboardButton("🔗 دعوة صديق", callback_data="ref")
    )
    if uid == ADMIN_ID:
        m.add(telebot.types.InlineKeyboardButton("🔱 لوحة التحكم 🔱", callback_data="admin_main"))
    return m

# --- [ مسار الويب هوك لفيرسل ] ---
@app.route('/api', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_json())
        bot.process_new_updates([update])
        return ''
    return 'Forbidden', 403

# --- [ معالجة الأوامر ] ---
@bot.message_handler(commands=['start'])
def start(m):
    if not is_sub(m.from_user.id):
        return bot.send_message(m.chat.id, f"⚠️ يجب الاشتراك أولاً: {CHANNEL}")
    
    bot.send_message(m.chat.id, "🔱 مرحباً بك في متجر القيصر المطور 🔱", reply_markup=main_markup(m.from_user.id))

@bot.callback_query_handler(func=lambda c: True)
def handle_cb(c):
    uid = c.from_user.id
    # منطق لوحة التحكم الشاملة
    if c.data == "admin_main" and uid == ADMIN_ID:
        m = telebot.types.InlineKeyboardMarkup()
        m.add(telebot.types.InlineKeyboardButton("➕ إضافة منتج", callback_data="add_p"))
        m.add(telebot.types.InlineKeyboardButton("❌ حذف منتج/ملف", callback_data="del_p"))
        m.add(telebot.types.InlineKeyboardButton("📢 إذاعة", callback_data="broadcast"))
        bot.edit_message_text("⚙️ لوحة تحكم المطور الشاملة:", c.message.chat.id, c.message.message_id, reply_markup=m)

# هذا السطر ضروري لعمل Flask مع Vercel
def handler(request):
    return app(request)

