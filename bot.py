import os
import sqlite3
import telebot
from telebot import types
import math
import logging
import threading
import time
import requests
from flask import Flask
import csv
import io

# Logging စနစ်
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8753076212:AAHBn4zvIYrrSr3XJTumF6ZgHRSqQqWbT8U"
ADMIN_ID = 8668319365
CHANNEL_USERNAME = "@starmobile63956"  # သင့်ရဲ့ Channel Username
ITEMS_PER_PAGE = 5  # တစ်မျက်နှာလျှင် ပြမည့် နံပါတ်အရေအတွက်

bot = telebot.TeleBot(TOKEN)

# ----------------------------------------------------
# 🔄 Render Web Service မပိတ်သွားစေရန် Flask & 5-Min Auto-Ping
# ----------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "VIP Phone Numbers Bot is running 24/7 successfully!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def auto_ping():
    # Render External URL ကို ယူသုံးမည်။ မရှိပါက localhost ကို ping ပါမည်။
    url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:10000')
    while True:
        try:
            time.sleep(300)  # ၅ မိနစ် (စက္ကန့် ၃၀၀) တိုင်း Ping မည်
            response = requests.get(url)
            logging.info(f"Auto-ping sent to {url} - Status: {response.status_code}")
        except Exception as e:
            logging.error(f"Ping failed: {e}")

# Web Server Thread
server_thread = threading.Thread(target=run_web_server)
server_thread.daemon = True
server_thread.start()

# Auto-Ping Thread
ping_thread = threading.Thread(target=auto_ping)
ping_thread.daemon = True
ping_thread.start()

# ----------------------------------------------------
# 🗄️ Database တည်ဆောက်ခြင်း
# ----------------------------------------------------
def init_db():
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT,
                operator TEXT,
                price REAL,
                num_type TEXT,
                status TEXT DEFAULT 'AVAILABLE'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                customer_name TEXT,
                chosen_number TEXT,
                price REAL,
                contact_info TEXT,
                ref_id INTEGER,
                status TEXT DEFAULT 'PENDING',
                date TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT
            )
        ''')
        conn.commit()

init_db()

def register_user(user_id, first_name):
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))
        conn.commit()

# 🔍 ဖုန်းနံပါတ်ကိုကြည့်၍ Operator အလိုအလျောက် ရှာဖွေပေးသည့် Function
def detect_operator(phone):
    p = ''.join(filter(str.isdigit, phone))
    if p.startswith('959'):
        p = '0' + p[2:]
    elif not p.startswith('0'):
        p = '09' + p
        
    if p.startswith(('0975', '0976', '0977', '0978', '0979')):
        return 'ATOM'
    elif p.startswith(('099', '0995', '0996', '0997', '0998', '0999')):
        return 'Ooredoo'
    elif p.startswith(('096', '0966', '0967', '0968', '0969', '0965', '0964')):
        return 'Mytel'
    elif p.startswith(('092', '094', '095', '098', '091')):
        return 'MPT'
    else:
        return 'Other'

# 🔔 Channel Join ပြီးကြောင်း စစ်ဆေးသည့် Function
def check_user_channel(user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        pass
    return False

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("✨ နံပါတ်လှများကြည့်မည်"),
        types.KeyboardButton("🍀 Lucky Phone ကြည့်မည်")
    )
    markup.add(
        types.KeyboardButton("📡 Operator အလိုက်ကြည့်မည်"),
        types.KeyboardButton("🔍 နံပါတ်ရှာမည်")
    )
    markup.add(
        types.KeyboardButton("💰 ဈေးနှုန်းအလိုက် ရှာမည်"),
        types.KeyboardButton("📦 ကျွန်ုပ်၏ အော်ဒါများ")
    )
    markup.add(types.KeyboardButton("📞 ဆိုင်နှင့် ဆက်သွယ်ရန်"))
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("👑 Admin Panel"))
    return markup

def not_joined_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Channel သို့သွားရန်", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"),
        types.InlineKeyboardButton("✅ Join ပြီးပါပြီ (စစ်ဆေးမည်)", callback_data="check_join")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    register_user(user_id, message.from_user.first_name)
    
    if not check_user_channel(user_id):
        text = (
            "⚠️ *ကျေးဇူးပြု၍ ကျွန်ုပ်တို့၏ Channel ကို အရင် Join ပေးပါ။*\n\n"
            "Bot ကို စတင်အသုံးပြုရန် အောက်ပါ Channel ကို Join ပြီးမှ **'✅ Join ပြီးပါပြီ'** ကို နှိပ်ပေးပါ။"
        )
        bot.send_message(message.chat.id, text, reply_markup=not_joined_markup(), parse_mode="Markdown")
        return

    text = (
        "✨ *Phone Numbers Sales Bot မှ ကြိုဆိုပါတယ်။*\n\n"
        "နံပါတ်လှများနှင့် Lucky Phone များကို အောက်ပါ ခလုတ်များမှတစ်ဆင့် ရွေးချယ် ဝယ်ယူနိုင်ပါပြီခင်ဗျာ။"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu(user_id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def verify_join_callback(call):
    user_id = call.from_user.id
    register_user(user_id, call.from_user.first_name)
    if check_user_channel(user_id):
        bot.answer_callback_query(call.id, "ကျေးဇူးတင်ပါတယ်! Channel Join ပြီးသားဖြစ်တာကို စစ်ဆေးတွေ့ရှိရပါပြီ။")
        text = (
            "✨ *Phone Numbers Sales Bot မှ ကြိုဆိုပါတယ်။*\n\n"
            "နံပါတ်လှများနှင့် Lucky Phone များကို အောက်ပါ ခလုတ်များမှတစ်ဆင့် ရွေးချယ် ဝယ်ယူနိုင်ပါပြီခင်ဗျာ။"
        )
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, text, reply_markup=main_menu(user_id), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။", show_alert=True)

def require_channel_join(func):
    def wrapper(message):
        if not check_user_channel(message.from_user.id):
            text = "⚠️ ဤစနစ်ကို အသုံးပြုရန်အတွက် ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။"
            bot.send_message(message.chat.id, text, reply_markup=not_joined_markup(), parse_mode="Markdown")
            return
        return func(message)
    return wrapper

# ✨ နံပါတ်လှများ ပြသခြင်း
@bot.message_handler(func=lambda m: m.text == "✨ နံပါတ်လှများကြည့်မည်")
@require_channel_join
def show_pro_numbers(message):
    send_paginated_numbers(message.chat.id, "PRO", 0, is_edit=False, message_id=None)

# 🍀 Lucky Phone ပြသခြင်း
@bot.message_handler(func=lambda m: m.text == "🍀 Lucky Phone ကြည့်မည်")
@require_channel_join
def show_lucky_numbers(message):
    send_paginated_numbers(message.chat.id, "LUCKY", 0, is_edit=False, message_id=None)

def send_paginated_numbers(chat_id, n_type, page, is_edit=False, message_id=None):
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM numbers WHERE num_type=? AND status='AVAILABLE'", (n_type,))
        total_items = cursor.fetchone()[0]

    if total_items == 0:
        text = "📭 လောလောဆယ် ဤစာရင်းတွင် နံပါတ်များ မရှိသေးပါ။"
        if is_edit:
            bot.edit_message_text(text, chat_id, message_id)
        else:
            bot.send_message(chat_id, text)
        return

    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    offset = page * ITEMS_PER_PAGE

    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone_number, operator, price FROM numbers WHERE num_type=? AND status='AVAILABLE' LIMIT ? OFFSET ?", (n_type, ITEMS_PER_PAGE, offset))
        rows = cursor.fetchall()

    title = "✨ ရောင်းရန်ရှိသော နံပါတ်လှများ -" if n_type == "PRO" else "🍀 ရောင်းရန်ရှိသော Lucky Phone များ -"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for row in rows:
        n_id, phone, op, price = row
        btn_text = f"📱 {phone} ({op}) - {price:,.0f} ကျပ်"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{n_id}"))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ ရှေ့သို့", callback_data=f"page_{n_type}_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("နောက်သို့ ➡️", callback_data=f"page_{n_type}_{page+1}"))
    
    if nav_buttons:
        markup.row(*nav_buttons)

    if is_edit:
        bot.edit_message_text(f"{title} (စာမျက်နှာ {page+1}/{total_pages})", chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, f"{title} (စာမျက်နှာ {page+1}/{total_pages})", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_"))
def handle_pagination(call):
    if not check_user_channel(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။", show_alert=True)
        return

    parts = call.data.split("_")
    n_type = parts[1]
    page = int(parts[2])
    send_paginated_numbers(call.message.chat.id, n_type, page, is_edit=True, message_id=call.message.message_id)

# 📡 Operator အလိုက် ခွဲခြားပြခြင်း
@bot.message_handler(func=lambda m: m.text == "📡 Operator အလိုက်ကြည့်မည်")
@require_channel_join
def show_operators(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("MPT", callback_data="op_MPT"),
        types.InlineKeyboardButton("ATOM", callback_data="op_ATOM"),
        types.InlineKeyboardButton("Ooredoo", callback_data="op_Ooredoo"),
        types.InlineKeyboardButton("Mytel", callback_data="op_Mytel")
    )
    bot.send_message(message.chat.id, "ကြည့်ရှုလိုသော အော်ပရေတာကို ရွေးချယ်ပါ -", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("op_"))
def filter_by_operator(call):
    if not check_user_channel(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။", show_alert=True)
        return

    op_name = call.data.split("_")[1]
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone_number, price, num_type FROM numbers WHERE operator=? AND status='AVAILABLE'", (op_name,))
        rows = cursor.fetchall()

    if not rows:
        bot.answer_callback_query(call.id, f"{op_name} နံပါတ်များ လောလောဆယ် မရှိသေးပါ။")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for row in rows:
        n_id, phone, price, n_type = row
        tag = "✨ နံပါတ်လှ" if n_type == "PRO" else "🍀 Lucky"
        btn_text = f"[{tag}] {phone} - {price:,.0f} ကျပ်"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{n_id}"))
            
    bot.edit_message_text(f"📡 *{op_name}* ရရှိနိုင်သော နံပါတ်များ -", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# 💰 ဈေးနှုန်းအလိုက် ရှာဖွေခြင်း
@bot.message_handler(func=lambda m: m.text == "💰 ဈေးနှုန်းအလိုက် ရှာမည်")
@require_channel_join
def price_filter_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔹 ၁ သိန်းအောက်", callback_data="pr_0_100000"),
        types.InlineKeyboardButton("🔹 ၁ သိန်း - ၅ သိန်း", callback_data="pr_100000_500000"),
        types.InlineKeyboardButton("🔹 ၅ သိန်း - ၁၀ သိန်း", callback_data="pr_500000_1000000"),
        types.InlineKeyboardButton("🔹 ၁၀ သိန်းအထက်", callback_data="pr_1000000_999999999")
    )
    bot.send_message(message.chat.id, "💰 ကြည့်ရှုလိုသော ဈေးနှုန်းအကွာအဝေးကို ရွေးချယ်ပါ -", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pr_"))
def filter_by_price(call):
    if not check_user_channel(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။", show_alert=True)
        return

    parts = call.data.split("_")
    min_p = float(parts[1])
    max_p = float(parts[2])

    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone_number, operator, price, num_type FROM numbers WHERE price BETWEEN ? AND ? AND status='AVAILABLE'", (min_p, max_p))
        rows = cursor.fetchall()

    if not rows:
        bot.answer_callback_query(call.id, "ဤဈေးနှုန်းအတွင်း ရရှိနိုင်သော နံပါတ်များ မရှိသေးပါ။", show_alert=True)
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for row in rows:
        n_id, phone, op, price, n_type = row
        tag = "✨ နံပါတ်လှ" if n_type == "PRO" else "🍀 Lucky"
        btn_text = f"[{tag}] {phone} ({op}) - {price:,.0f} ကျပ်"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{n_id}"))

    bot.edit_message_text("💰 ရွေးချယ်ထားသော ဈေးနှုန်းအတွင်းရှိ နံပါတ်များ -", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# 🔍 နံပါတ်ရှာဖွေခြင်း
@bot.message_handler(func=lambda m: m.text == "🔍 နံပါတ်ရှာမည်")
@require_channel_join
def search_number(message):
    msg = bot.send_message(message.chat.id, "🔍 သင်ရှာဖွေလိုသော ဂဏန်းကို ရိုက်ထည့်ပါ\n*(ဥပမာ - 777 သို့မဟုတ် 9999)*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    if not check_user_channel(message.from_user.id):
        return

    keyword = message.text.strip()
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone_number, operator, price, num_type FROM numbers WHERE phone_number LIKE ? AND status='AVAILABLE'", (f'%{keyword}%',))
        rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, f"❌ `{keyword}` ပါဝင်သော နံပါတ်များ ရှာမတွေ့ပါ။", parse_mode="Markdown")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for row in rows:
        n_id, phone, op, price, n_type = row
        tag = "✨ နံပါတ်လှ" if n_type == "PRO" else "🍀 Lucky"
        btn_text = f"[{tag}] {phone} ({op}) - {price:,.0f} ကျပ်"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{n_id}"))
    
    bot.send_message(message.chat.id, f"🔍 `{keyword}` ပါဝင်သော နံပါတ်များ -", reply_markup=markup, parse_mode="Markdown")

# 📦 ကျွန်ုပ်၏ အော်ဒါများ
@bot.message_handler(func=lambda m: m.text == "📦 ကျွန်ုပ်၏ အော်ဒါများ" or m.text == "/myorders")
@require_channel_join
def show_my_orders(message):
    user_id = message.from_user.id
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, chosen_number, price, contact_info, status, date FROM orders WHERE user_id=? AND status='PENDING'", (user_id,))
        rows = cursor.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "📭 လောလောဆယ် ဆောင်ရွက်ဆဲ (Pending) အော်ဒါမှတ်တမ်း မရှိပါ။")
        return

    for row in rows:
        o_id, phone, price, contact_info, status, date = row
        order_code = f"#ORD-{o_id:03d}"
        
        text = (
            f"📦 **အော်ဒါနံပါတ်:** `{order_code}`\n"
            f"📱 **မှာယူသည့်နံပါတ်:** `{phone}`\n"
            f"💰 **ကျသင့်ငွေ:** `{price:,.0f}` ကျပ်\n"
            f"📍 **လိပ်စာ:** {contact_info}\n"
            f"📅 **ရက်စွဲ:** {date}\n"
            f"📌 **အခြေအနေ:** ဆောင်ရွက်ဆဲ (Pending)"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ ဤအော်ဒါကို ဖျက်သိမ်းမည် (Cancel)", callback_data=f"user_cancel_ord_{o_id}"))
        
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("user_cancel_ord_"))
def cancel_user_order(call):
    o_id = int(call.data.split("_")[3])
    user_id = call.from_user.id

    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ref_id, chosen_number FROM orders WHERE id=? AND user_id=?", (o_id, user_id))
        order = cursor.fetchone()

        if order:
            ref_id, phone = order
            if ref_id:
                cursor.execute("UPDATE numbers SET status='AVAILABLE' WHERE id=?", (ref_id,))
            cursor.execute("DELETE FROM orders WHERE id=?", (o_id,))
            conn.commit()

            bot.answer_callback_query(call.id, "အော်ဒါကို အောင်မြင်စွာ ဖျက်သိမ်းလိုက်ပါပြီ။", show_alert=True)
            bot.edit_message_text(f"❌ *အော်ဒါ #{o_id:03d} (`{phone}`) ကို သင်ကိုယ်တိုင် ဖျက်သိမ်းလိုက်ပါပြီ။*", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
            try:
                bot.send_message(ADMIN_ID, f"ℹ️ ဝယ်သူ ({call.from_user.first_name}) သည် အော်ဒါ #{o_id:03d} (`{phone}`) ကို ကိုယ်တိုင် ဖျက်သိမ်းလိုက်ပါသည်။ နံပါတ်ကို ပြန်ဖွင့်ပေးလိုက်ပါပြီ။", parse_mode="Markdown")
            except Exception:
                pass
        else:
            bot.answer_callback_query(call.id, "အော်ဒါ မတွေ့ရှိရတော့ပါ။", show_alert=True)

# 🛒 ဝယ်ယူရန် အော်ဒါတင်ခြင်း
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    if not check_user_channel(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပေးပါ။", show_alert=True)
        return

    n_id = call.data.split("_")[1]
    with sqlite3.connect('vip_shop.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT phone_number, price, status FROM numbers WHERE id=?", (n_id,))
        item = cursor.fetchone()

    if not item or item[2] == 'SOLD':
        bot.answer_callback_query(call.id, "ဤနံပါတ် ရောင်းထွက်သွားပြီ (သို့) မရှိတော့ပါ။", show_alert=True)
        return

    phone, price, _ = item
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ ဝယ်ယူမှုကို ဖျက်သိမ်းမည် (Cancel)", callback_data=f"cancel_buy_{n_id}"))

    msg = bot.send_message(
        call.message.chat.id, 
        f"🎯 သင်ရွေးချယ်ထားသော နံပါတ် - *{phone}*\n"
        f"💰 ကျသင့်ငွေ (ဖုန်းဘိုး) - `{price:,.0f}` ကျပ်\n\n"
        f"📦 *အိမ်ရောက်ငွေချေ (COD) ဖြင့် ပို့ဆောင်ပေးမည်ဖြစ်ပါသည်။*\n"
        f"သို့သော် Deli ခ **`4,000`** ကျပ်ကို အရင်ကြိုတင်လွှဲပေးရပါမည်။\n\n"
        f"💳 **Deli ခ 4,000 လွှဲရန် အကောင့်များ:**\n"
        f"🔹 *KPay:* `09795096484` (Si Thu Aung)\n"
        f"🔹 *WavePay:* `09792654163` (Si Thu Aung)\n\n"
        f"📝 Deli ခလွှဲပြီးပါက ပစ္စည်းပို့ရန်အတွက် သင်၏ **နာမည်၊ ဖုန်းနံပါတ် နှင့် လိပ်စာအတိအကျ** ကို အောက်ပါပုံစံအတိုင်း ရိုက်ထည့်ပေးပါ -\n\n"
        f"*(ဥပမာ - မောင်မောင်၊ 09792654163၊ အမှတ်(၁၂)၊ ဗိုလ်ချုပ်လမ်း၊ ရန်ကုန်)*",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, save_order, phone, price, n_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_buy_"))
def user_cancel_buy(call):
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    try:
        bot.edit_message_text("❌ *ဝယ်ယူမှုကို ဖျက်သိမ်းလိုက်ပါပြီ။*", call.message
