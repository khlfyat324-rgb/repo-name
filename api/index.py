import os
import json
import base64
import requests
import telebot
from flask import Flask, request

# --- [ استخراج المفاتيح - السيطرة الكاملة ] ---
TOKEN = os.environ.get("BOT_TOKEN")
GH_TOKEN = os.environ.get("GH_TOKEN")
REPO = os.environ.get("REPO_NAME")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8294538151"))
CHANNEL = os.environ.get("CHANNEL_ID", "@zsewwi")
DEV_USER = "@F_l1t"

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- [ نظام إدارة البيانات عبر GitHub ] ---
def github_manage(path, method="GET", content=None, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    if method == "GET":
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            res = r.json()
            return json.loads(base64.b64decode(res['content']).decode('utf-8')), res['sha']
        return {"users": {}, "items": {"nums": [], "paid": [], "free": []}}, None
    
    elif method == "PUT":
        payload = {
            "message": "Update Store Data",
            "content": base64.b64encode(json.dumps(content, indent=4).encode('utf-8')).decode('utf-8'),
            "sha": sha
        }
        return requests.put(url, headers=headers, json=payload).status_code

# --- [ الأزرار والواجهات الأسطورية ] ---
def build_menu(uid):
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    m.add(
        telebot.types.InlineKeyboardButton("📱 قسم الأرقام الأمريكية", callback_data="sec_nums"),
        telebot.types.InlineKeyboardButton("💰 الأدوات المدفوعة", callback_data="sec_paid")
    )
    m.add(
        telebot.types.InlineKeyboardButton("🎁 الأدوات المجانية", callback_data="sec_free"),
        telebot.types.InlineKeyboardButton("👤 حسابي", callback_data="profile")
    )
    m.add(
        telebot.types.InlineKeyboardButton("🔗 رابط الإحالة", callback_data="referral"),
        telebot.types.InlineKeyboardButton("⚠️ الإبلاغ عن مشكلة", callback_data="report_issue")
    )
    if uid == ADMIN_ID:
        m.add(telebot.types.InlineKeyboardButton("🔱 لوحة تحكم المطور 🔱", callback_data="admin_panel"))
    return m

# --- [Middleware: التحقق من الاشتراك ] ---
def check_membership(uid):
    try:
        s = bot.get_chat_member(CHANNEL, uid).status
        return s in ['member', 'administrator', 'creator']
    except: return False

# --- [ استقبال التحديثات من تليجرام ] ---
@app.route('/api', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return '403'

# --- [ معالجة الأوامر الرئيسية ] ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = m.from_user.id
    if not check_membership(uid):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ اضغط هنا للاشتراك أولاً", url=f"https://t.me/{CHANNEL.replace('@','')}"))
        return bot.send_message(m.chat.id, f"⚠️ عذراً عزيزي، يجب أن تكون عضواً في قناتنا لتتمكن من استخدام المتجر واستعراض الأدوات:\n\n{CHANNEL}", reply_markup=markup)

    bot.send_message(m.chat.id, "👋 أهلاً بك في متجر القيصر المطور.\nتمتع بتجربة شراء وتحميل فريدة من نوعها.", reply_markup=build_menu(uid))

# --- [ معالجة أزرار الاستجابة (Callback) ] ---
@bot.callback_query_handler(func=lambda c: True)
def process_callbacks(c):
    uid = c.from_user.id
    cid = c.message.chat.id
    mid = c.message.message_id

    # -- الأقسام العامة --
    if c.data == "sec_nums":
        bot.edit_message_text("📱 **قسم الأرقام الأمريكية الحصرية:**\n\nجميع الأرقام تعمل 100% ويتم تسليمها فورياً بـ 50 نجمة تليجرام.", cid, mid, parse_mode="Markdown")
    
    elif c.data == "report_issue":
        bot.edit_message_text(f"⚠️ واجهت مشكلة؟ تواصل مع المطور مباشرة:\n\nالاسم: إبراهيم\nالمعرف: {DEV_USER}", cid, mid)

    # -- لوحة التحكم الملكية للمطور فقط --
    elif c.data == "admin_panel" and uid == ADMIN_ID:
        adm = telebot.types.InlineKeyboardMarkup(row_width=2)
        adm.add(
            telebot.types.InlineKeyboardButton("➕ إضافة أداة", callback_data="adm_add"),
            telebot.types.InlineKeyboardButton("❌ حذف أداة من GitHub", callback_data="adm_del"),
            telebot.types.InlineKeyboardButton("📢 إذاعة شاملة", callback_data="adm_broadcast"),
            telebot.types.InlineKeyboardButton("📊 إحصائيات", callback_data="adm_stats"),
            telebot.types.InlineKeyboardButton("🔙 العودة", callback_data="main_menu")
        )
        bot.edit_message_text("🔱 مرحباً بك يا سيدي المطور في لوحة التحكم الشاملة.\nماذا تريد أن تفعل الآن؟", cid, mid, reply_markup=adm)

    elif c.data == "main_menu":
        bot.edit_message_text("🔱 متجر القيصر المطور 🔱", cid, mid, reply_markup=build_menu(uid))

    bot.answer_callback_query(c.id)

def handler(request):
    return app(request)

