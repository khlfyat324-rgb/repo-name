import os
import json
import base64
import requests
import telebot
from flask import Flask, request

# --- [ الإعدادات ] ---
TOKEN = os.environ.get("BOT_TOKEN")
GH_TOKEN = os.environ.get("GH_TOKEN")
REPO = os.environ.get("REPO_NAME")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8294538151"))
CHANNEL = "@zsewwi"

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- [ محرك GitHub - التحكم الشامل ] ---
def manage_db(action="read", data=None):
    url = f"https://api.github.com/repos/{REPO}/contents/db.json"
    headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    res = r.json()
    sha = res.get('sha')
    
    # إذا لم يوجد الملف، ننشئ هيكل أساسي
    if r.status_code != 200:
        base = {"users": {}, "categories": ["📱 أرقام", "🛠️ أدوات مدفوعة", "🎁 أدوات مجانية"], "products": [], "settings": {"ref": 0.5}, "states": {}}
        manage_db("write", base)
        return base

    db = json.loads(base64.b64decode(res['content']).decode('utf-8'))
    if action == "read": return db
    if action == "write":
        new_c = base64.b64encode(json.dumps(data, indent=4).encode('utf-8')).decode('utf-8')
        requests.put(url, headers=headers, json={"message": "Update", "content": new_c, "sha": sha})

# --- [ واجهات المستخدم ] ---
def main_kb(uid):
    db = manage_db("read")
    m = telebot.types.InlineKeyboardMarkup(row_width=2)
    for cat in db.get('categories', []):
        m.add(telebot.types.InlineKeyboardButton(cat, callback_data=f"v_cat_{cat}"))
    m.add(telebot.types.InlineKeyboardButton("👤 حسابي", callback_data="acc"), 
          telebot.types.InlineKeyboardButton("🔗 دعوة", callback_data="ref"))
    if uid == ADMIN_ID:
        m.add(telebot.types.InlineKeyboardButton("🔱 لوحة التحكم الشاملة 🔱", callback_data="adm"))
    return m

# --- [ الويب هوك ] ---
@app.route('/api', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_json())])
    return '', 200

# --- [ معالجة الرسائل ] ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'document'])
def handle_msgs(m):
    uid = m.from_user.id
    db = manage_db("read")
    state = db.get("states", {}).get(str(uid))

    if m.text == "/start":
        return bot.send_message(m.chat.id, "🥷 **أهلاً بك في متجر القيصر**", reply_markup=main_kb(uid), parse_mode="Markdown")

    # --- [ منطق الإضافة ] ---
    if uid == ADMIN_ID and state:
        if state == "add_c": # إضافة قسم
            db['categories'].append(m.text)
            db['states'][str(uid)] = None
            manage_db("write", db)
            bot.send_message(m.chat.id, f"✅ تم إضافة قسم: {m.text}")
        
        elif isinstance(state, dict) and state.get('a') == "add_p": # إضافة منتج
            step = state.get('s')
            if step == "n":
                state.update({"n": m.text, "s": "p"})
                db['states'][str(uid)] = state
                manage_db("write", db)
                return bot.send_message(m.chat.id, "💰 أرسل السعر:")
            elif step == "p":
                state.update({"p": m.text, "s": "f"})
                db['states'][str(uid)] = state
                manage_db("write", db)
                return bot.send_message(m.chat.id, "📎 أرسل الملف أو الرقم:")
            elif step == "f":
                content = m.document.file_id if m.document else m.text
                db['products'].append({"cat": state['c'], "name": state['n'], "price": state['p'], "file": content})
                db['states'][str(uid)] = None
                manage_db("write", db)
                return bot.send_message(m.chat.id, "✅ تم الحفظ بنجاح!")

# --- [ معالجة الأزرار ] ---
@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid, cid, mid = c.from_user.id, c.message.chat.id, c.message.message_id
    db = manage_db("read")

    # عرض المنتجات حسب القسم
    if c.data.startswith("v_cat_"):
        cat = c.data.replace("v_cat_", "")
        prods = [p for p in db.get('products', []) if p['cat'] == cat]
        if not prods: return bot.answer_callback_query(c.id, "⚠️ لا توجد منتجات هنا.")
        
        txt = f"📂 القسم: **{cat}**\n\n"
        m = telebot.types.InlineKeyboardMarkup()
        for i, p in enumerate(prods):
            price = "مجاني 🎁" if p['price'] in ["0", "مجاني", "0$"] else f"{p['price']}"
            txt += f"{i+1}️⃣ {p['name']} | {price}\n"
            m.add(telebot.types.InlineKeyboardButton(f"شراء: {p['name']}", callback_data=f"buy_{i}_{cat}"))
        m.add(telebot.types.InlineKeyboardButton("🔙 عودة", callback_data="home"))
        bot.edit_message_text(txt, cid, mid, reply_markup=m, parse_mode="Markdown")

    # لوحة التحكم الشاملة
    elif c.data == "adm" and uid == ADMIN_ID:
        m = telebot.types.InlineKeyboardMarkup(row_width=2)
        m.add(telebot.types.InlineKeyboardButton("➕ إضافة قسم", callback_data="adm_ac"),
              telebot.types.InlineKeyboardButton("📦 إضافة منتج", callback_data="adm_ap"),
              telebot.types.InlineKeyboardButton("🗑️ حذف منتج", callback_data="adm_dp"),
              telebot.types.InlineKeyboardButton("❌ حذف قسم", callback_data="adm_dc"),
              telebot.types.InlineKeyboardButton("🔙 عودة", callback_data="home"))
        bot.edit_message_text("⚙️ **لوحة التحكم المطلقة**", cid, mid, reply_markup=m, parse_mode="Markdown")

    elif c.data == "adm_ac": # طلب اسم القسم
        db['states'][str(uid)] = "add_c"
        manage_db("write", db)
        bot.send_message(cid, "📝 أرسل اسم القسم الجديد:")

    elif c.data == "adm_ap": # اختيار قسم للمنتج
        m = telebot.types.InlineKeyboardMarkup()
        for cat in db['categories']:
            m.add(telebot.types.InlineKeyboardButton(cat, callback_data=f"sel_{cat}"))
        bot.edit_message_text("📂 اختر القسم للإضافة إليه:", cid, mid, reply_markup=m)

    elif c.data.startswith("sel_"):
        cat = c.data.replace("sel_", "")
        db['states'][str(uid)] = {"a": "add_p", "s": "n", "c": cat}
        manage_db("write", db)
        bot.send_message(cid, f"🏷️ أرسل اسم المنتج لـ {cat}:")

    elif c.data == "adm_dp": # حذف منتج
        m = telebot.types.InlineKeyboardMarkup()
        for i, p in enumerate(db['products']):
            m.add(telebot.types.InlineKeyboardButton(f"❌ {p['name']} ({p['cat']})", callback_data=f"delp_{i}"))
        m.add(telebot.types.InlineKeyboardButton("🔙", callback_data="adm"))
        bot.edit_message_text("🗑️ اختر المنتج المراد حذفه نهائياً:", cid, mid, reply_markup=m)

    elif c.data.startswith("delp_"):
        idx = int(c.data.split("_")[1])
        del db['products'][idx]
        manage_db("write", db)
        bot.answer_callback_query(c.id, "✅ تم الحذف!")
        handle_calls(telebot.types.CallbackQuery(c.id, c.from_user, c.message, c.inline_message_id, "adm_dp"))

    elif c.data == "home":
        bot.edit_message_text("🥷 **القائمة الرئيسية**", cid, mid, reply_markup=main_kb(uid), parse_mode="Markdown")

def handler(request):
    return app(request)

