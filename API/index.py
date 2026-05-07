import os
import json
import telebot
from fastapi import FastAPI, Request
from github import Github

# إعداد المتغيرات من البيئة
API_TOKEN = os.getenv("BOT_TOKEN")
GH_TOKEN = os.getenv("GH_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8294538151"))
REPO_NAME = os.getenv("REPO_NAME") # اسم مستودعك لتخزين البيانات
CHANNEL_ID = "@zsewwi" # يوزر القناة للاشتراك الإجباري

bot = telebot.TeleBot(API_TOKEN)
app = FastAPI()
gh = Github(GH_TOKEN)

# دالة للتحقق من الاشتراك الإجباري
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

# دالة لجلب قاعدة البيانات من GitHub
def get_db():
    repo = gh.get_repo(REPO_NAME)
    contents = repo.get_contents("db.json")
    return json.loads(contents.decoded_content.decode())

# دالة لتحديث قاعدة البيانات على GitHub
def update_db(data):
    repo = gh.get_repo(REPO_NAME)
    contents = repo.get_contents("db.json")
    repo.update_file(contents.path, "Update DB", json.dumps(data, indent=4), contents.sha)

@app.post(f"/{API_TOKEN}")
async def process_update(request: Request):
    json_string = await request.json()
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "ok"

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("اضغط هنا للاشتراك", url=f"https://t.me/zsewwi"))
        return bot.send_message(message.chat.id, "❌ يجب عليك الاشتراك في القناة أولاً لاستخدام البوت!", reply_markup=markup)

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn1 = telebot.types.InlineKeyboardButton("🎁 الأدوات المجانية", callback_data="free")
    btn2 = telebot.types.InlineKeyboardButton("💰 الأدوات المدفوعة", callback_data="paid")
    btn3 = telebot.types.InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    markup.add(btn1, btn2, btn3)
    
    if user_id == ADMIN_ID:
        markup.add(telebot.types.InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel"))

    bot.send_message(message.chat.id, "👋 أهلاً بك في متجر ستار للأدوات!\nاختر ما يناسبك من الأقسام أدناه:", reply_markup=markup)

# لوحة تحكم الأدمين
@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel(call):
    if call.from_user.id != ADMIN_ID: return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("➕ إضافة أداة", callback_data="add_tool"))
    markup.add(telebot.types.InlineKeyboardButton("📢 رسالة جماعية", callback_data="broadcast"))
    bot.edit_message_text("🛠 لوحة تحكم المطور:", call.message.chat.id, call.message.message_id, reply_markup=markup)

# إضافة أداة (أدمن فقط)
@bot.callback_query_handler(func=lambda call: call.data == "add_tool")
def add_tool_step1(call):
    msg = bot.send_message(call.message.chat.id, "أرسل اسم الأداة:")
    bot.register_next_step_handler(msg, add_tool_step2)

def add_tool_step2(message):
    tool_name = message.text
    msg = bot.send_message(message.chat.id, "أرسل سعر الأداة (0 للمجاني):")
    bot.register_next_step_handler(msg, add_tool_step3, tool_name)

def add_tool_step3(message, tool_name):
    price = float(message.text)
    msg = bot.send_message(message.chat.id, "الآن أرسل ملف الأداة:")
    bot.register_next_step_handler(msg, save_tool, tool_name, price)

def save_tool(message, tool_name, price):
    if not message.document:
        return bot.send_message(message.chat.id, "❌ خطأ! يجب إرسال ملف.")
    
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    # رفع الملف إلى GitHub
    repo = gh.get_repo(REPO_NAME)
    repo.create_file(f"tools/{message.document.file_name}", f"Add {tool_name}", downloaded_file)
    
    # تحديث قاعدة البيانات
    db = get_db()
    db['tools'].append({
        "name": tool_name,
        "price": price,
        "file_path": f"tools/{message.document.file_name}"
    })
    update_db(db)
    bot.send_message(message.chat.id, "✅ تم حفظ الأداة ورفعها بنجاح!")

# قسم الأدوات المجانية والمدفوعة
@bot.callback_query_handler(func=lambda call: call.data in ["free", "paid"])
def list_tools(call):
    db = get_db()
    markup = telebot.types.InlineKeyboardMarkup()
    is_paid = (call.data == "paid")
    
    for tool in db['tools']:
        if (is_paid and tool['price'] > 0) or (not is_paid and tool['price'] == 0):
            markup.add(telebot.types.InlineKeyboardButton(f"{tool['name']} - {tool['price']}$", callback_data=f"buy_{tool['name']}"))
            
    bot.edit_message_text("الأدوات المتاحة:", call.message.chat.id, call.message.message_id, reply_markup=markup)

# عند طلب أداة
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    tool_name = call.data.split("_")[1]
    db = get_db()
    tool = next((t for t in db['tools'] if t['name'] == tool_name), None)
    
    if tool['price'] == 0:
        repo = gh.get_repo(REPO_NAME)
        file_content = repo.get_contents(tool['file_path'])
        bot.send_document(call.message.chat.id, file_content.download_url, caption=f"🎁 إليك أداتك المجانية: {tool_name}")
    else:
        # هنا يتم التحقق من رصيد الدولار (يمكنك إضافة منطق الخصم من الرصيد هنا)
        bot.answer_callback_query(call.id, "سيتم توجيهك للدفع بالدولار...")


