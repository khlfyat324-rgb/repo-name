import os
import json
import base64
import requests
import telebot
from flask import Flask, request

# --- [ جلب المفاتيح من Vercel ] ---
TOKEN = os.environ.get("BOT_TOKEN")
GH_TOKEN = os.environ.get("GH_TOKEN")
REPO = os.environ.get("REPO_NAME")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8294538151"))
CHANNEL = "@zsewwi"

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- [ محرك GitHub للتحكم الشامل ] ---
def manage_db(action="read", data=None):
    url = f"https://api.github.com/repos/{REPO}/contents/db.json"
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    r = requests.get(url, headers=headers)
    sha = r.json().get('sha') if r.status_code == 200 else None
    current_content = json.loads(base64.b64decode(r.json()['content']).decode('utf-8')) if sha else {
        "users": {}, "categories": ["📱 أرقام", "🛠️ أدوات مدفوعة", "🎁 أدوات مجانية"],
        "products": [], "settings": {"ref_price": 0.5}, "states": {}
    }

    if action == "read": return current_content
    
    if action == "write":
        new_content = base64.b64encode(json.dumps(data, indent=4).encode('utf-8')).decode('utf-8')
        requests.put(url, headers=headers, json={"message": "Update DB", "content": new_content, "sha": sha})

# --- [ التحقق من الاشتراك الإجباري ] ---
def check_sub(uid):
    try:
        s = bot.get_chat_member(CHANNEL, uid).status
        return s in ['member', 'administrator', 'creator']
    except: return False

# --- [ كيبورد المتجر ] ---
def main_kb(uid):
    db = manage_db("read")
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    for cat in db['categories']:
        m.add(telebot.types.InlineKeyboardButton(cat, callback_data=f"view_cat_{cat}"))
    
    m.add(telebot.types.InlineKeyboardButton("👤 حسابي", callback_data="my_acc"),
          telebot.types.InlineKeyboardButton("🔗 دعوة", callback_data="ref"))
    
    if uid == ADMIN_ID:
        m.add(telebot.types.InlineKeyboardButton("⚙️ لوحة التحكم الشاملة", callback_data="admin_panel"))
    return m

# --- [ معالجة الويب هوك ] ---
@app.route('/api', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_json())])
    return '', 200

# --- [ استقبال الرسائل والتحكم بالحالات ] ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'document'])
def handle_all_messages(m):
    uid = m.from_user.id
    db = manage_db("read")
    state = db.get("states", {}).get(str(uid))

    if m.text == "/start":
        if not check_sub(uid):
            return bot.send_message(m.chat.id, f"🚫 **يجب الاشتراك أولاً:** {CHANNEL}")
        
        # نظام الإحالة (إذا دخل من رابط شخص آخر)
        args = m.text.split()
        if len(args) > 1 and str(uid) not in db['users']:
            ref_id = args[1]
            if ref_id != str(uid):
                db['users'][ref_id]['balance'] = db['users'].get(ref_id, {}).get('balance', 0) + db['settings']['ref_price']
        
        if str(uid) not in db['users']:
            db['users'][str(uid)] = {"balance": 0, "invited": 0}
            manage_db("write", db)
            
        return bot.send_message(m.chat.id, "🥷 **مرحباً بك في متجر القيصر**\nتصفح الأقسام أدناه:", reply_markup=main_kb(uid), parse_mode="Markdown")

    # --- [ منطق إضافة قسم جديد ] ---
    if state == "add_category_name" and uid == ADMIN_ID:
        db['categories'].append(m.text)
        db['states'][str(uid)] = None
        manage_db("write", db)
        return bot.send_message(m.chat.id, f"✅ تم إضافة قسم: **{m.text}** بنجاح!")

    # --- [ منطق إضافة منتج (أداة أو رقم) ] ---
    if isinstance(state, dict) and state.get('action') == "adding_product" and uid == ADMIN_ID:
        step = state.get('step')
        
        if step == "name":
            state['name'] = m.text
            state['step'] = "price"
            db['states'][str(uid)] = state
            manage_db("write", db)
            return bot.send_message(m.chat.id, "💰 أرسل السعر (مثلاً: 0.75 أو 50 للنجوم):")
            
        if step == "price":
            state['price'] = m.text
            state['step'] = "file"
            db['states'][str(uid)] = state
            manage_db("write", db)
            return bot.send_message(m.chat.id, "📎 أرسل الآن ملف الأداة أو 'رقم' (نص):")

        if step == "file":
            content = m.text if m.text else m.document.file_id
            db['products'].append({
                "cat": state['cat'], "name": state['name'], 
                "price": state['price'], "content": content
            })
            db['states'][str(uid)] = None
            manage_db("write", db)
            return bot.send_message(m.chat.id, "✅ **تم إضافة المنتج للمتجر بنجاح!**")

# --- [ معالجة الأزرار ] ---
@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    uid, cid = c.from_user.id, c.message.chat.id
    db = manage_db("read")

    if c.data == "admin_panel" and uid == ADMIN_ID:
        m = telebot.types.InlineKeyboardMarkup(row_width=2)
        m.add(telebot.types.InlineKeyboardButton("➕ إضافة قسم", callback_data="add_cat"),
              telebot.types.InlineKeyboardButton("📦 إضافة منتج", callback_data="add_prod"),
              telebot.types.InlineKeyboardButton("⚙️ سعر الإحالة", callback_data="set_ref"),
              telebot.types.InlineKeyboardButton("📢 إذاعة", callback_data="bc"))
        bot.edit_message_text("🛠️ **لوحة التحكم الشاملة**", cid, c.message.message_id, reply_markup=m, parse_mode="Markdown")

    if c.data == "add_cat" and uid == ADMIN_ID:
        db['states'][str(uid)] = "add_category_name"
        manage_db("write", db)
        bot.send_message(cid, "📝 أرسل اسم القسم الجديد (مثلاً: حسابات فيسبوك):")

    if c.data == "add_prod" and uid == ADMIN_ID:
        m = telebot.types.InlineKeyboardMarkup()
        for cat in db['categories']:
            m.add(telebot.types.InlineKeyboardButton(cat, callback_data=f"sel_cat_{cat}"))
        bot.edit_message_text("📂 اختر القسم الذي تريد الإضافة إليه:", cid, c.message.message_id, reply_markup=m)

    if c.data.startswith("sel_cat_") and uid == ADMIN_ID:
        cat = c.data.replace("sel_cat_", "")
        db['states'][str(uid)] = {"action": "adding_product", "step": "name", "cat": cat}
        manage_db("write", db)
        bot.send_message(cid, f"🏷️ أرسل اسم المنتج لقسم **{cat}**:")

# --- [ تشغيل Vercel ] ---
def handler(request):
    return app(request)

