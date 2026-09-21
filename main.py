import sqlite3
import telebot
from telebot import types
import os
import time
import requests
from flask import Flask
from threading import Thread
import pandas as pd
import io
import pytz
from datetime import datetime
import pymongo

# ----------------- MongoDB Setup -----------------
MONGO_URI = "mongodb+srv://User:310199@cluster0.oys0fgi.mongodb.net/?appName=Cluster0" 

def sync_db_from_mongo():
    if MONGO_URI == "YOUR_MONGODB_URI_HERE": return
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client['accounting_bot']
        doc = db.backups.find_one({"name": "accounting.db"})
        if doc:
            with open('accounting.db', 'wb') as f:
                f.write(doc['data'])
            print("✅ MongoDB မှ Database အဟောင်းကို အောင်မြင်စွာ ဆွဲယူပြီးပါပြီ။")
    except Exception as e:
        print("MongoDB မှ ဆွဲယူရာတွင် အမှားရှိနေပါသည်:", e)

def sync_db_to_mongo():
    if MONGO_URI == "YOUR_MONGODB_URI_HERE": return
    try:
        if os.path.exists('accounting.db'):
            with open('accounting.db', 'rb') as f:
                data = f.read()
            client = pymongo.MongoClient(MONGO_URI)
            db = client['accounting_bot']
            db.backups.update_one(
                {"name": "accounting.db"},
                {"$set": {"data": data}},
                upsert=True
            )
            print("✅ MongoDB သို့ Database အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ။")
            
    except Exception as e:
        print("MongoDB သို့ သိမ်းရာတွင် အမှားရှိနေပါသည်:", e)
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, f"⚠️ <b>MongoDB Sync Error:</b>\nBackup သိမ်းဆည်းရာတွင် အမှားရှိနေပါသည်။\n\nError: {e}", parse_mode="HTML")
            except:
                pass

def auto_sync_mongo():
    while True:
        time.sleep(1800) 
        sync_db_to_mongo()

# ----------------- Ping & Auto Backup Setup -----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running and awake!"

def run_server():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def self_ping():
    RENDER_URL = "https://caarng-kiung-cash.onrender.com" 
    while True:
        time.sleep(600) 
        try:
            requests.get(RENDER_URL)
            print(f"Ping successful: Kept awake at {time.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"Ping failed: {e}")

def schedule_daily_backup():
    tz = pytz.timezone('Asia/Yangon')
    while True:
        now = datetime.now(tz)
        if now.hour == 0 and now.minute == 0:
            sync_db_to_mongo() 
            for admin_id in ADMIN_IDS:
                try:
                    if os.path.exists('accounting.db'):
                        with open('accounting.db', 'rb') as f:
                            bot.send_document(admin_id, f, caption=f"📦 နေ့စဉ် Database Backup (Auto)\nDate: {now.strftime('%Y-%m-%d %I:%M %p')}")
                except Exception as e:
                    print("Auto backup error:", e)
            time.sleep(60) 
        time.sleep(30) 

def keep_alive():
    server_thread = Thread(target=run_server)
    server_thread.start()
    ping_thread = Thread(target=self_ping)
    ping_thread.start()
    backup_thread = Thread(target=schedule_daily_backup)
    backup_thread.start()
    mongo_thread = Thread(target=auto_sync_mongo)
    mongo_thread.start()
# -----------------------------------------------------------------

TOKEN = "8580240882:AAGL-RQdlmIOSm4VUx7y07l-ZY43HOrmdOY"
bot = telebot.TeleBot(TOKEN)
ADMIN_IDS = [8668319365] 

def init_db():
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, amount REAL, note TEXT, date TIMESTAMP DEFAULT (datetime('now', 'localtime')))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_name TEXT, quantity INTEGER DEFAULT 0, buy_price REAL DEFAULT 0, sell_price REAL DEFAULT 0, rented_out INTEGER DEFAULT 0, rented_in INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS stock_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action_type TEXT, item_name TEXT, qty INTEGER, trans_id INTEGER, deli_trans_id INTEGER, date TIMESTAMP DEFAULT (datetime('now', 'localtime')))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS salaries (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, emp_name TEXT, amount REAL, date TIMESTAMP DEFAULT (datetime('now', 'localtime')), status TEXT DEFAULT 'unpaid')''')
    
    try: cursor.execute('ALTER TABLE inventory ADD COLUMN rented_out INTEGER DEFAULT 0')
    except: pass
    try: cursor.execute('ALTER TABLE inventory ADD COLUMN rented_in INTEGER DEFAULT 0')
    except: pass
    try: cursor.execute('ALTER TABLE stock_logs ADD COLUMN deli_trans_id INTEGER')
    except: pass

    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def is_cancel(message):
    if message.text in ["🔙 ပင်မမီနူးသို့", "🔙 Stock မီနူးသို့", "🔄 အငှားကဏ္ဍ (Rentals)", "📦 ဝယ်/ရောင်း/ငှား/stock"]:
        if "ပင်မ" in message.text:
            bot.send_message(message.chat.id, "ပင်မမီနူးသို့ ပြန်ရောက်ပါပြီ။", reply_markup=main_menu())
        elif "Stock" in message.text or "ဝယ်/ရောင်း" in message.text:
            bot.send_message(message.chat.id, "📦 Stock မီနူးသို့ ပြန်ရောက်ပါပြီ။", reply_markup=stock_menu())
        else:
            bot.send_message(message.chat.id, "လုပ်ဆောင်ချက် ပယ်ဖျက်လိုက်ပါသည်။", reply_markup=main_menu())
        return True
    return False

# ----- Safe Callback Answer Helper -----
def answer_cb(call_id, text=None):
    """Network ကြောင့် Callback ပြတ်ကျခြင်းမှ ကာကွယ်ပေးသော Function"""
    try:
        if text:
            bot.answer_callback_query(callback_query_id=call_id, text=text)
        else:
            bot.answer_callback_query(callback_query_id=call_id)
    except Exception as e:
        print(f"Callback answer timeout (Safe ignored): {e}")

# ----------------- Pagination Helpers -----------------
def make_pagination_keyboard(page_cb_prefix, current_page, total_pages):
    markup = types.InlineKeyboardMarkup(row_width=3)
    if total_pages > 1:
        nav_btns = []
        if current_page > 0: nav_btns.append(types.InlineKeyboardButton("⬅️ ယခင်", callback_data=f"{page_cb_prefix}_{current_page - 1}"))
        else: nav_btns.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
            
        nav_btns.append(types.InlineKeyboardButton(f"📑 {current_page + 1} / {total_pages}", callback_data="ignore"))
        
        if current_page < total_pages - 1: nav_btns.append(types.InlineKeyboardButton("နောက် ➡️", callback_data=f"{page_cb_prefix}_{current_page + 1}"))
        else: nav_btns.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
        markup.row(*nav_btns)
    return markup

def make_item_pagination_keyboard(items, item_cb_prefix, page_cb_prefix, current_page, total_pages):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for item_id, text in items:
        markup.add(types.InlineKeyboardButton(text, callback_data=f"{item_cb_prefix}_{item_id}"))
    
    if total_pages > 1:
        nav_btns = []
        if current_page > 0: nav_btns.append(types.InlineKeyboardButton("⬅️ ယခင်", callback_data=f"{page_cb_prefix}_{current_page - 1}"))
        else: nav_btns.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
            
        nav_btns.append(types.InlineKeyboardButton(f"📑 {current_page + 1} / {total_pages}", callback_data="ignore"))
        
        if current_page < total_pages - 1: nav_btns.append(types.InlineKeyboardButton("နောက် ➡️", callback_data=f"{page_cb_prefix}_{current_page + 1}"))
        else: nav_btns.append(types.InlineKeyboardButton(" ", callback_data="ignore"))
        markup.row(*nav_btns)
        
    markup.add(types.InlineKeyboardButton("✖️ မလုပ်တော့ပါ (ပိတ်မည်)", callback_data="cancel_reset"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "ignore")
def handle_ignore(call):
    answer_cb(call.id)

# ----------------- Helper Functions -----------------
def get_available_stock_html(user_id, condition="quantity > 0"):
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    if condition == "quantity > 0":
        cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id=? AND quantity > 0", (user_id,))
    elif condition == "rented_out > 0":
        cursor.execute("SELECT item_name, rented_out FROM inventory WHERE user_id=? AND rented_out > 0", (user_id,))
    elif condition == "rented_in > 0":
        cursor.execute("SELECT item_name, rented_in FROM inventory WHERE user_id=? AND rented_in > 0", (user_id,))
    else:
        cursor.execute("SELECT item_name, quantity FROM inventory WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows: return "📦 <i>ပြသရန် Stock မရှိသေးပါ။</i>\n\n"
    text = "📦 <b>ရွေးချယ်နိုင်သော Stock များ:</b>\n(အမည်ကို နှိပ်၍ Copy ကူးပါ)\n"
    for r in rows: text += f"▪️ <code>{r[0]}</code> - (လက်ကျန်: {r[1]} ခု)\n"
    return text + "\n"

def get_total_stock_value(user_id):
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT quantity, rented_out, rented_in, buy_price FROM inventory WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    total_val = 0
    for qty, r_out, r_in, price in rows:
        r_out = r_out or 0
        r_in = r_in or 0
        owned_qty = qty + r_out - r_in
        total_val += owned_qty * price
    return total_val

# ----------------- Menus -----------------
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("➕ ဝင်ငွေမှတ်မည်"), types.KeyboardButton("➖ ထွက်ငွေမှတ်မည်"))
    markup.add(types.KeyboardButton("📅 ဒီနေ့စာရင်း"), types.KeyboardButton("🗓 ဒီလစာရင်း"))
    markup.add(types.KeyboardButton("🗓 ဒီနှစ်စာရင်း"), types.KeyboardButton("💰 စုစုပေါင်းလက်ကျန်"))
    markup.add(types.KeyboardButton("📦 ဝယ်/ရောင်း/ငှား/stock"), types.KeyboardButton("👥 အလုပ်သမားလစာ"))
    markup.add(types.KeyboardButton("💾 Backup / Recover (Data)"), types.KeyboardButton("❌ စာရင်းဖျက်မည်"))
    markup.add(types.KeyboardButton("🔄 အသစ်ပြန်စမည်"))
    return markup

def stock_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("🛒 ဝယ်မည် (Buy)"), types.KeyboardButton("🛍 ရောင်းမည် (Sell)"))
    markup.add(types.KeyboardButton("📦 Stock အဟောင်းသွင်းမည်"), types.KeyboardButton("🗑 ပျက်စီး/အလျော့ပြ"))
    markup.add(types.KeyboardButton("🔄 အငှားကဏ္ဍ (Rentals)"), types.KeyboardButton("📊 Stock တန်ဖိုး/လက်ကျန်"))
    markup.add(types.KeyboardButton("↩️ မှားသွားလျှင် ပြန်ဖျက်မည်"), types.KeyboardButton("🔙 ပင်မမီနူးသို့"))
    return markup

def rent_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("📥 အငှားယူမည် (Borrow)"), types.KeyboardButton("📤 အငှားပြန်အပ်မည်"))
    markup.add(types.KeyboardButton("📤 အငှားပေးမည် (Lend)"), types.KeyboardButton("📥 အငှားပြန်ရမည်"))
    markup.add(types.KeyboardButton("🔙 Stock မီနူးသို့"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    add_user(message.from_user.id)
    text = "မင်္ဂလာပါ! စာရင်းကိုင်နှင့် Stock Bot မှ ကြိုဆိုပါတယ်။\nအောက်ပါ ခလုတ်များကို နှိပ်၍ အသုံးပြုနိုင်ပါသည်။"
    bot.send_message(message.chat.id, text, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 ပင်မမီနူးသို့")
def back_to_main(message):
    bot.send_message(message.chat.id, "ပင်မမီနူးသို့ ပြန်ရောက်ပါပြီ။", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 Stock မီနူးသို့")
def back_to_stock(message):
    bot.send_message(message.chat.id, "📦 Stock မီနူးသို့ ပြန်ရောက်ပါပြီ။", reply_markup=stock_menu())

@bot.message_handler(func=lambda m: m.text in ["📦 ဝယ်/ရောင်း/ငှား/stock", "ဝယ်/ရောင်း/ငှား/stock"])
def show_stock_menu(message):
    bot.send_message(message.chat.id, "📦 Stock စီမံခန့်ခွဲမှု စနစ်မှ ကြိုဆိုပါတယ်။", reply_markup=stock_menu())

@bot.message_handler(func=lambda m: m.text == "🔄 အငှားကဏ္ဍ (Rentals)")
def show_rent_menu(message):
    bot.send_message(message.chat.id, "🔄 အငှားဝန်ဆောင်မှု စနစ်", reply_markup=rent_menu())

# ----------------- စာရင်းမှတ်ခြင်း (ငွေကြေး) -----------------
@bot.message_handler(func=lambda m: m.text in ["➕ ဝင်ငွေမှတ်မည်", "➖ ထွက်ငွေမှတ်မည်"])
def start_transaction(message):
    trans_type = 'income' if 'ဝင်ငွေ' in message.text else 'expense'
    msg = bot.send_message(message.chat.id, "ပမာဏနှင့် အကြောင်းအရာကို ရိုက်ထည့်ပါ\n(ဥပမာ - 5000 လစာ သို့မဟုတ် 1500 မနက်စာ):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_transaction, trans_type)

def process_transaction(message, trans_type):
    if is_cancel(message): return
    try:
        parts = message.text.split(maxsplit=1)
        amount = float(parts[0])
        note = parts[1] if len(parts) > 1 else "အခြား" 
        
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, ?, ?, ?)",
                       (message.from_user.id, trans_type, amount, note))
        conn.commit()
        conn.close()
        
        type_str = "➕ ဝင်ငွေ" if trans_type == 'income' else "➖ ထွက်ငွေ"
        res = f"✅ စာရင်းမှတ်ပြီးပါပြီ!\n\nအမျိုးအစား: {type_str}\nပမာဏ: {amount:,.0f} Ks\nအကြောင်းအရာ: {note}"
        bot.send_message(message.chat.id, res, reply_markup=main_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ မှားယွင်းနေပါသည်။ ပမာဏကို အရင်ရိုက်ပါ (ဥပမာ- 2000 မုန့်ဖိုး)။", reply_markup=main_menu())

# ----------------- STOCK မီနူးများ -----------------
@bot.message_handler(func=lambda m: m.text == "🛒 ဝယ်မည် (Buy)")
def ask_buy_stock(message):
    stock_list = get_available_stock_html(message.from_user.id, "all")
    text = stock_list + "ဝယ်ယူမည့် ပစ္စည်းအမည်၊ အရေအတွက်၊ ဝယ်ဈေး(တစ်ခုစာ) ကို ကော်မာ (,) ခြား၍ ရိုက်ထည့်ပါ။\n(ပို့ဆောင်ခ ရှိပါက အဆုံးတွင် ထည့်သွင်းနိုင်ပါသည်။)\n\nဥပမာ: <code>ဖုန်း, 5, 100000, 2000</code>"
    msg = bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_buy_stock)

def process_buy_stock(message):
    if is_cancel(message): return
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name, qty, buy_price = parts[0], int(parts[1]), float(parts[2])
        deli_fee = float(parts[3]) if len(parts) > 3 else 0.0
        
        total_expense = qty * buy_price
        user_id = message.from_user.id
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, quantity FROM inventory WHERE user_id=? AND item_name=?", (user_id, name))
        row = cursor.fetchone()
        
        if row:
            new_qty = row[1] + qty
            cursor.execute("UPDATE inventory SET quantity=?, buy_price=? WHERE id=?", (new_qty, buy_price, row[0]))
        else:
            new_qty = qty
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity, buy_price) VALUES (?, ?, ?, ?)", (user_id, name, qty, buy_price))
            
        cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'expense', ?, ?)", (user_id, total_expense, f"{name} ဝယ်ယူခြင်း"))
        trans_id = cursor.lastrowid
        
        deli_trans_id = None
        if deli_fee > 0:
            cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'expense', ?, ?)", (user_id, deli_fee, f"{name} ဝယ်ယူရန် ပို့ဆောင်ခ"))
            deli_trans_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id, deli_trans_id) VALUES (?, 'buy', ?, ?, ?, ?)", (user_id, name, qty, trans_id, deli_trans_id))
        conn.commit()
        conn.close()
        
        res_text = f"✅ ဝယ်ယူမှုမှတ်တမ်း တင်ပြီးပါပြီ။\n\nပစ္စည်း: {name}\nအဝယ်အရေအတွက်: {qty}\nစုစုပေါင်းကျသင့်ငွေ: {total_expense:,.0f} Ks"
        if deli_fee > 0: res_text += f"\n🚚 ပို့ဆောင်ခ (ထွက်ငွေ): {deli_fee:,.0f} Ks"
        res_text += f"\n📦 ယခု Stock လက်ကျန်: {new_qty} ခု"
        bot.send_message(message.chat.id, res_text, reply_markup=stock_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။ (ဥပမာ: ဖုန်း, 5, 100000)", reply_markup=stock_menu())

@bot.message_handler(func=lambda m: m.text == "🛍 ရောင်းမည် (Sell)")
def ask_sell_stock(message):
    stock_list = get_available_stock_html(message.from_user.id, "quantity > 0")
    text = stock_list + "ရောင်းမည့် ပစ္စည်းအမည်၊ အရေအတွက်၊ ရောင်းဈေး(တစ်ခုစာ) ကို ကော်မာ (,) ခြား၍ ရိုက်ပါ။\n\nဥပမာ: <code>ဖုန်း, 2, 150000, 3000</code>"
    msg = bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_sell_stock)

def process_sell_stock(message):
    if is_cancel(message): return
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name, qty, sell_price = parts[0], int(parts[1]), float(parts[2])
        deli_fee = float(parts[3]) if len(parts) > 3 else 0.0
        
        user_id = message.from_user.id
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, quantity FROM inventory WHERE user_id=? AND item_name=?", (user_id, name))
        row = cursor.fetchone()
        
        if not row or row[1] < qty:
            conn.close()
            bot.send_message(message.chat.id, f"⚠️ '{name}' အတွက် Stock မလုံလောက်ပါ။", reply_markup=stock_menu())
            return
            
        new_qty = row[1] - qty
        total_income = qty * sell_price
        cursor.execute("UPDATE inventory SET quantity=?, sell_price=? WHERE id=?", (new_qty, sell_price, row[0]))
        cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'income', ?, ?)", (user_id, total_income, f"{name} ရောင်းရငွေ"))
        trans_id = cursor.lastrowid
        
        deli_trans_id = None
        if deli_fee > 0:
            cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'expense', ?, ?)", (user_id, deli_fee, f"{name} ရောင်းချရန် ပို့ဆောင်ခ"))
            deli_trans_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id, deli_trans_id) VALUES (?, 'sell', ?, ?, ?, ?)", (user_id, name, qty, trans_id, deli_trans_id))
        conn.commit()
        conn.close()
        
        res_text = f"✅ ရောင်းချမှု အောင်မြင်ပါသည်။\n\nပစ္စည်း: {name} ({qty} ခု)\nစုစုပေါင်းရငွေ: {total_income:,.0f} Ks"
        if deli_fee > 0: res_text += f"\n🚚 ပို့ဆောင်ခ (ထွက်ငွေ): {deli_fee:,.0f} Ks"
        res_text += f"\n📦 ယခု Stock လက်ကျန်: {new_qty} ခု"
        bot.send_message(message.chat.id, res_text, reply_markup=stock_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။ (ဥပမာ: ဖုန်း, 2, 150000)", reply_markup=stock_menu())

@bot.message_handler(func=lambda m: m.text == "📦 Stock အဟောင်းသွင်းမည်")
def ask_old_stock(message):
    stock_list = get_available_stock_html(message.from_user.id, "all")
    msg = bot.send_message(message.chat.id, stock_list + "ယခင်ရှိပြီးသား Stock အဟောင်းများ ထည့်သွင်းရန်\nဥပမာ: <code>ဖုန်း, 5, 100000</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_old_stock)

def process_old_stock(message):
    if is_cancel(message): return
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name, qty, buy_price = parts[0], int(parts[1]), float(parts[2])
        user_id = message.from_user.id
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, quantity FROM inventory WHERE user_id=? AND item_name=?", (user_id, name))
        row = cursor.fetchone()
        
        if row:
            new_qty = row[1] + qty
            cursor.execute("UPDATE inventory SET quantity=?, buy_price=? WHERE id=?", (new_qty, buy_price, row[0]))
        else:
            new_qty = qty
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity, buy_price) VALUES (?, ?, ?, ?)", (user_id, name, qty, buy_price))
            
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id, deli_trans_id) VALUES (?, 'old_stock', ?, ?, NULL, NULL)", (user_id, name, qty))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ Stock အဟောင်း ထည့်သွင်းခြင်း အောင်မြင်ပါသည်။\n\nပစ္စည်း: {name}\nအရေအတွက်: +{qty}\n📦 ယခု Stock လက်ကျန်: {new_qty} ခု", reply_markup=stock_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။", reply_markup=stock_menu())

@bot.message_handler(func=lambda m: m.text == "🗑 ပျက်စီး/အလျော့ပြ")
def ask_damage_stock(message):
    stock_list = get_available_stock_html(message.from_user.id, "quantity > 0")
    msg = bot.send_message(message.chat.id, stock_list + "ပျက်စီး/ပျောက်ဆုံးသွားသော ပစ္စည်းအမည် နှင့် အရေအတွက်ကို ရိုက်ပါ။\nဥပမာ: <code>ဖုန်း, 1</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_damage_stock)

def process_damage_stock(message):
    if is_cancel(message): return
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name, qty = parts[0], int(parts[1])
        user_id = message.from_user.id
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, quantity FROM inventory WHERE user_id=? AND item_name=?", (user_id, name))
        row = cursor.fetchone()
        if not row or row[1] < qty:
            conn.close()
            bot.send_message(message.chat.id, "⚠️ Stock အလုံအလောက်မရှိပါ။", reply_markup=stock_menu())
            return
        new_qty = row[1] - qty
        cursor.execute("UPDATE inventory SET quantity=? WHERE id=?", (new_qty, row[0]))
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id, deli_trans_id) VALUES (?, 'damage', ?, ?, NULL, NULL)", (user_id, name, qty))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"🗑 {name} ({qty} ခု) စာရင်းမှ ပယ်ဖျက်လိုက်ပါပြီ။\n📦 ယခု Stock လက်ကျန်: {new_qty} ခု", reply_markup=stock_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။", reply_markup=stock_menu())

# ================== အငှားကဏ္ဍ (RENTALS) ==================

@bot.message_handler(func=lambda m: m.text == "📤 အငှားပေးမည် (Lend)")
def ask_lend_stock(message):
    stock_list = get_available_stock_html(message.from_user.id, "quantity > 0")
    msg = bot.send_message(message.chat.id, stock_list + "သူတစ်ပါးထံ အငှားပေးမည့် ပစ္စည်းအမည်၊ အရေအတွက်၊ ပို့ဆောင်ခ(Delivery-မရှိလျှင် 0) ကို ကော်မာ(,) ခြား၍ ရိုက်ပါ။\nဥပမာ: <code>ဖုန်း, 2, 1000</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_lend_stock)

def process_lend_stock(message):
    if is_cancel(message): return
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name, qty = parts[0], int(parts[1])
        deli_fee = float(parts[2]) if len(parts) > 2 else 0.0
        user_id = message.from_user.id
        
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, quantity, rented_out FROM inventory WHERE user_id=? AND item_name=?", (user_id, name))
        row = cursor.fetchone()
        
        if not row or row[1] < qty:
            conn.close()
            bot.send_message(message.chat.id, "⚠️ ငှားပေးရန် သင့်ထံတွင် Stock လက်ကျန် အလုံအလောက်မရှိပါ။", reply_markup=rent_menu())
            return
            
        deli_trans_id = None
        if deli_fee > 0:
            cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'expense', ?, ?)", (user_id, deli_fee, f"{name} အငှားပေးရန် ပို့ဆောင်ခ"))
            deli_trans_id = cursor.lastrowid
            
        new_qty = row[1] - qty 
        new_rented_out = (row[2] if row[2] else 0) + qty 
        
        cursor.execute("UPDATE inventory SET quantity=?, rented_out=? WHERE id=?", (new_qty, new_rented_out, row[0]))
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id, deli_trans_id) VALUES (?, 'lend', ?, ?, NULL, ?)", (user_id, name, qty, deli_trans_id))
        conn.commit()
        conn.close()
        
        text = f"✅ {name} ({qty} ခု) ကို အငှားပေးလိုက်ပါပြီ။\n📦 သင့်လက်ကျန်: {new_qty} ခု"
        if deli_fee > 0: text += f"\n🚚 ပို့ဆောင်ခ (ထွက်ငွေ): {deli_fee:,.0f} Ks"
        bot.send_message(message.chat.id, text, reply_markup=rent_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။ (ဥပမာ: ဖုန်း, 2, 1000)", reply_markup=rent_menu())

@bot.message_handler(func=lambda m: m.text == "📥 အငှားပြန်ရမည်")
def ask_receive_rented(message):
    stock_list = get_available_stock_html(message.from_user.id, "rented_out > 0")
    msg = bot.send_message(message.chat.id, stock_list + "ပြန်လည်လက်ခံရရှိမည့် ပစ္စည်းအမည်၊ အရေအတွက်၊ ငှားရမ်းခ(ရရှိမည့်ငွေ)၊ Delivery ခ(ရှိလျှင်) ကို ကော်မာ(,) ခြား၍ ရိုက်ပါ။\nဥပမာ: <code>ဖုန်း, 1, 3000, 1000</code>\n(ငှားခမရှိပါက 0 ဟုထည့်ပါ)", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_receive_rented)

def process_receive_rented(message):
    if is_cancel(message): return
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name, qty = parts[0], int(parts[1])
        rent_fee = float(parts[2]) if len(parts) > 2 else 0.0
        deli_fee = float(parts[3]) if len(parts) > 3 else 0.0
        user_id = message.from_user.id
        
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, quantity, rented_out FROM inventory WHERE user_id=? AND item_name=?", (user_id, name))
        row = cursor.fetchone()
        
        if not row or (row[2] if row[2] else 0) < qty:
            conn.close()
            bot.send_message(message.chat.id, "⚠️ သင်ငှားထားသော အရေအတွက်ထက် ပိုများနေပါသည်။", reply_markup=rent_menu())
            return
            
        trans_id = None
        if rent_fee > 0:
            cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'income', ?, ?)", (user_id, rent_fee, f"{name} အငှားပေးခဲ့သော ငှားခရရှိခြင်း"))
            trans_id = cursor.lastrowid
            
        deli_trans_id = None
        if deli_fee > 0:
            cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'expense', ?, ?)", (user_id, deli_fee, f"{name} ပြန်လည်ရယူရန် ပို့ဆောင်ခ"))
            deli_trans_id = cursor.lastrowid
            
        new_qty = row[1] + qty 
        new_rented_out = row[2] - qty 
        
        cursor.execute("UPDATE inventory SET quantity=?, rented_out=? WHERE id=?", (new_qty, new_rented_out, row[0]))
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id, deli_trans_id) VALUES (?, 'return_lend', ?, ?, ?, ?)", (user_id, name, qty, trans_id, deli_trans_id))
        conn.commit()
        conn.close()
        
        text = f"✅ အငှားပေးထားသော {name} ({qty} ခု) ပြန်လည်ရရှိပါပြီ။"
        if rent_fee > 0: text += f"\n💸 ငှားရမ်းခ (ဝင်ငွေ): {rent_fee:,.0f} Ks"
        if deli_fee > 0: text += f"\n🚚 ပို့ဆောင်ခ (ထွက်ငွေ): {deli_fee:,.0f} Ks"
        bot.send_message(message.chat.id, text, reply_markup=rent_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။ (ဥပမာ: ဖုန်း, 1, 3000, 1000)", reply_markup=rent_menu())

@bot.message_handler(func=lambda m: m.text == "📥 အငှားယူမည် (Borrow)")
def ask_borrow_stock(message):
    msg = bot.send_message(message.chat.id, "သူတစ်ပါးထံမှ ငှားယူလာမည့် ပစ္စည်းအမည်၊ အရေအတွက်၊ ပို့ဆောင်ခ(Delivery-မရှိလျှင် 0) ကို ကော်မာ(,) ခြား၍ ရိုက်ပါ။\nဥပမာ: <code>စက်ဘီး, 3, 2000</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_borrow_stock)

def process_borrow_stock(message):
    if is_cancel(message): return
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name, qty = parts[0], int(parts[1])
        deli_fee = float(parts[2]) if len(parts) > 2 else 0.0
        user_id = message.from_user.id
        
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        
        deli_trans_id = None
        if deli_fee > 0:
            cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'expense', ?, ?)", (user_id, deli_fee, f"{name} အငှားယူရန် ပို့ဆောင်ခ"))
            deli_trans_id = cursor.lastrowid
            
        cursor.execute("SELECT id, quantity, rented_in FROM inventory WHERE user_id=? AND item_name=?", (user_id, name))
        row = cursor.fetchone()
        
        if row:
            new_qty = row[1] + qty
            new_rented_in = (row[2] if row[2] else 0) + qty
            cursor.execute("UPDATE inventory SET quantity=?, rented_in=? WHERE id=?", (new_qty, new_rented_in, row[0]))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity, rented_in, buy_price, sell_price) VALUES (?, ?, ?, ?, 0, 0)", (user_id, name, qty, qty))
            
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id, deli_trans_id) VALUES (?, 'borrow', ?, ?, NULL, ?)", (user_id, name, qty, deli_trans_id))
        conn.commit()
        conn.close()
        
        text = f"✅ {name} ({qty} ခု) ကို အငှားယူလိုက်ပါပြီ။ သင့် Stock ထဲတွင် အသုံးပြုရန် အသင့်ဖြစ်ပါပြီ။"
        if deli_fee > 0: text += f"\n🚚 ပို့ဆောင်ခ (ထွက်ငွေ): {deli_fee:,.0f} Ks"
        bot.send_message(message.chat.id, text, reply_markup=rent_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။ (ဥပမာ: စက်ဘီး, 3, 2000)", reply_markup=rent_menu())

@bot.message_handler(func=lambda m: m.text == "📤 အငှားပြန်အပ်မည်")
def ask_return_borrowed(message):
    stock_list = get_available_stock_html(message.from_user.id, "rented_in > 0")
    msg = bot.send_message(message.chat.id, stock_list + "ပိုင်ရှင်ထံသို့ ပြန်အပ်မည့် ပစ္စည်းအမည်၊ အရေအတွက်၊ ငှားခ(ပေးရမည့်ငွေ)၊ Delivery ခ ကို ကော်မာ(,) ခြား၍ ရိုက်ပါ။\nဥပမာ: <code>စက်ဘီး, 1, 5000, 1500</code>\n(ငှားခမရှိပါက 0 ဟုထည့်ပါ)", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_return_borrowed)

def process_return_borrowed(message):
    if is_cancel(message): return
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name, qty = parts[0], int(parts[1])
        rent_fee = float(parts[2]) if len(parts) > 2 else 0.0
        deli_fee = float(parts[3]) if len(parts) > 3 else 0.0
        user_id = message.from_user.id
        
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, quantity, rented_in FROM inventory WHERE user_id=? AND item_name=?", (user_id, name))
        row = cursor.fetchone()
        
        if not row or (row[2] if row[2] else 0) < qty or row[1] < qty:
            conn.close()
            bot.send_message(message.chat.id, "⚠️ သင့်ထံတွင် ပြန်အပ်ရန် အရေအတွက် မလုံလောက်ပါ။ (သို့) ငှားထားသောစာရင်း မှားယွင်းနေပါသည်။", reply_markup=rent_menu())
            return
            
        trans_id = None
        if rent_fee > 0:
            cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'expense', ?, ?)", (user_id, rent_fee, f"{name} အငှားယူခဲ့သော ငှားခပေးခြင်း"))
            trans_id = cursor.lastrowid
            
        deli_trans_id = None
        if deli_fee > 0:
            cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'expense', ?, ?)", (user_id, deli_fee, f"{name} ပြန်အပ်ရန် ပို့ဆောင်ခ"))
            deli_trans_id = cursor.lastrowid
            
        new_qty = row[1] - qty
        new_rented_in = row[2] - qty
        
        cursor.execute("UPDATE inventory SET quantity=?, rented_in=? WHERE id=?", (new_qty, new_rented_in, row[0]))
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id, deli_trans_id) VALUES (?, 'return_borrow', ?, ?, ?, ?)", (user_id, name, qty, trans_id, deli_trans_id))
        conn.commit()
        conn.close()
        
        text = f"✅ ငှားယူထားသော {name} ({qty} ခု) ကို ပိုင်ရှင်ထံ ပြန်လည်အပ်နှံပြီးပါပြီ။"
        if rent_fee > 0: text += f"\n💸 ငှားရမ်းခ (ထွက်ငွေ): {rent_fee:,.0f} Ks"
        if deli_fee > 0: text += f"\n🚚 ပို့ဆောင်ခ (ထွက်ငွေ): {deli_fee:,.0f} Ks"
        bot.send_message(message.chat.id, text, reply_markup=rent_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။ (ဥပမာ: စက်ဘီး, 1, 5000, 1500)", reply_markup=rent_menu())

# ----------------- 📊 Stock Valuation (Pagination ဖြင့်) -----------------
def get_stock_val_page(user_id, page):
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity, rented_out, rented_in, buy_price FROM inventory WHERE user_id=?", (user_id,))
    all_rows = cursor.fetchall()
    
    total_items = len(all_rows)
    if total_items == 0:
        conn.close()
        return None, 0, 0
        
    grand_total_value = 0
    for _, qty, r_out, r_in, price in all_rows:
        r_out = r_out or 0
        r_in = r_in or 0
        owned_qty = qty + r_out - r_in
        grand_total_value += owned_qty * price
        
    per_page = 5
    total_pages = (total_items + per_page - 1) // per_page
    
    cursor.execute("SELECT item_name, quantity, rented_out, rented_in, buy_price FROM inventory WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (user_id, per_page, page * per_page))
    rows = cursor.fetchall()
    conn.close()
    
    text = f"📊 <b>Stock စာရင်း (စာမျက်နှာ {page+1}/{total_pages})</b>\n=========================\n\n"
    for r in rows:
        name, qty, r_out, r_in, buy_price = r
        r_out = r_out or 0
        r_in = r_in or 0
        owned_total = qty + r_out - r_in 
        item_value = owned_total * buy_price
        
        if qty > 0 or r_out > 0 or r_in > 0:
            text += f"🏷 <b>{name}</b>\n"
            text += f"   📦 လက်ကျန်: {qty} ခု\n"
            if r_out > 0: text += f"   📤 သူများကိုငှားထား: {r_out} ခု\n"
            if r_in > 0: text += f"   📥 သူများဆီမှငှားထား: {r_in} ခု\n"
            text += f"   💰 တန်ဖိုး: {owned_total} x {buy_price:,.0f} = <b>{item_value:,.0f} Ks</b>\n\n"
        
    text += f"=========================\n"
    text += f"🏆 <b>စုစုပေါင်း Stock တန်ဖိုး: {grand_total_value:,.0f} Ks</b>"
    return text, total_pages, grand_total_value

def send_stock_val_page(chat_id, user_id, page, message_id=None):
    text, total_pages, _ = get_stock_val_page(user_id, page)
    if text is None:
        if message_id: bot.edit_message_text(text="📦 ပစ္စည်း (Stock) စာရင်း အလွတ်ဖြစ်နေပါသည်။", chat_id=chat_id, message_id=message_id)
        else: bot.send_message(chat_id, "📦 ပစ္စည်း (Stock) စာရင်း အလွတ်ဖြစ်နေပါသည်။")
        return
        
    markup = make_pagination_keyboard("page_stockval", page, total_pages)
    if message_id: bot.edit_message_text(text=text, chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode="HTML")
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📊 Stock တန်ဖိုး/လက်ကျန်")
def check_stock_value(message):
    send_stock_val_page(message.chat.id, message.from_user.id, 0)

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_stockval_"))
def handle_stockval_page(call):
    answer_cb(call.id)
    page = int(call.data.split("_")[2])
    send_stock_val_page(call.message.chat.id, call.from_user.id, page, call.message.message_id)

# ----------------- Reports (အစီရင်ခံစာများ) -----------------
@bot.message_handler(func=lambda m: m.text == "📅 ဒီနေ့စာရင်း")
def show_today_report(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT type, amount, note, strftime('%H:%M', date) FROM transactions WHERE user_id=? AND date(date) = date('now', 'localtime') ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    cursor.execute("SELECT SUM(CASE WHEN type='income' THEN amount ELSE 0 END), SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) FROM transactions WHERE user_id=? AND date(date) = date('now', 'localtime')", (user_id,))
    total_inc, total_exp = cursor.fetchone()
    conn.close()
    
    total_inc = total_inc or 0.0
    total_exp = total_exp or 0.0
    
    if not rows:
        bot.send_message(message.chat.id, "📅 ဒီနေ့အတွက် မှတ်ထားသော ငွေကြေးစာရင်း မရှိသေးပါ။")
        return
        
    text = "📅 ဒီနေ့ စာရင်းချုပ်\n---------------------------\n"
    for row in rows:
        t_type, amount, note, time_str = row
        symbol = "🟢 +" if t_type == 'income' else "🔴 -"
        text += f"[{time_str}] {symbol} {amount:,.0f} Ks ({note})\n"
        
    text += f"---------------------------\n🟢 ဝင်ငွေ: {total_inc:,.0f} Ks\n🔴 ထွက်ငွေ: {total_exp:,.0f} Ks\n⚖️ လက်ကျန်: {(total_inc - total_exp):,.0f} Ks"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🗓 ဒီလစာရင်း")
def show_month_report(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT note, SUM(amount) FROM transactions WHERE user_id=? AND type='income' AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now', 'localtime') GROUP BY note ORDER BY SUM(amount) DESC", (user_id,))
    incomes = cursor.fetchall()
    cursor.execute("SELECT note, SUM(amount) FROM transactions WHERE user_id=? AND type='expense' AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now', 'localtime') GROUP BY note ORDER BY SUM(amount) DESC", (user_id,))
    expenses = cursor.fetchall()
    cursor.execute("SELECT SUM(CASE WHEN type='income' THEN amount ELSE 0 END), SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) FROM transactions WHERE user_id=? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now', 'localtime')", (user_id,))
    total_inc, total_exp = cursor.fetchone()
    conn.close()
    
    total_inc, total_exp = total_inc or 0.0, total_exp or 0.0
    
    text = "🗓 <b>ဒီလ ဘဏ္ဍာရေး အစီရင်ခံစာ (အကျဉ်းချုပ်)</b>\n=========================\n\n"
    if incomes:
        text += "🟢 <b>ဝင်ငွေ ခေါင်းစဉ်များ:</b>\n"
        for note, amt in incomes: text += f"▪️ {note}: {amt:,.0f} Ks\n"
        text += "\n"
    if expenses:
        text += "🔴 <b>ထွက်ငွေ ခေါင်းစဉ်များ:</b>\n"
        for note, amt in expenses: text += f"▪️ {note}: {amt:,.0f} Ks\n"
        text += "\n"
        
    text += "=========================\n"
    text += f"🟢 <b>ဒီလ ဝင်ငွေစုစုပေါင်း:</b> {total_inc:,.0f} Ks\n🔴 <b>ဒီလ ထွက်ငွေစုစုပေါင်း:</b> {total_exp:,.0f} Ks\n---------------------------\n"
    text += f"💵 <b>ဒီလ ပိုငွေ/လက်ကျန်:</b> {(total_inc - total_exp):,.0f} Ks\n📦 <b>လက်ရှိ Stock တန်ဖိုး:</b> {get_total_stock_value(user_id):,.0f} Ks\n"
    bot.send_message(message.chat.id, text[:4096], parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🗓 ဒီနှစ်စာရင်း")
def show_year_report(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT strftime('%m', date), SUM(CASE WHEN type='income' THEN amount ELSE 0 END), SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) FROM transactions WHERE user_id=? AND strftime('%Y', date) = strftime('%Y', 'now', 'localtime') GROUP BY strftime('%m', date) ORDER BY strftime('%m', date)", (user_id,))
    monthly_data = cursor.fetchall()
    cursor.execute("SELECT SUM(CASE WHEN type='income' THEN amount ELSE 0 END), SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) FROM transactions WHERE user_id=? AND strftime('%Y', date) = strftime('%Y', 'now', 'localtime')", (user_id,))
    total_inc, total_exp = cursor.fetchone()
    conn.close()
    
    total_inc, total_exp = total_inc or 0.0, total_exp or 0.0
    
    if not monthly_data:
        bot.send_message(message.chat.id, "🗓 ဤနှစ်အတွက် မှတ်တမ်း မရှိသေးပါ။")
        return
        
    text = "🗓 <b>ဒီနှစ် ဘဏ္ဍာရေး အစီရင်ခံစာ (နှစ်ချုပ်)</b>\n=========================\n\n"
    for month, m_inc, m_exp in monthly_data:
        m_inc, m_exp = m_inc or 0.0, m_exp or 0.0
        text += f"📅 <b>လ - {month}</b>:\n   🟢 ဝင်ငွေ: +{m_inc:,.0f}\n   🔴 ထွက်ငွေ: -{m_exp:,.0f}\n\n"
        
    text += "=========================\n"
    text += f"🟢 <b>ဒီနှစ် ဝင်ငွေစုစုပေါင်း:</b> {total_inc:,.0f} Ks\n🔴 <b>ဒီနှစ် ထွက်ငွေစုစုပေါင်း:</b> {total_exp:,.0f} Ks\n---------------------------\n"
    text += f"💵 <b>ဒီနှစ် ပိုငွေ/လက်ကျန်:</b> {(total_inc - total_exp):,.0f} Ks\n"
    bot.send_message(message.chat.id, text[:4096], parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "💰 စုစုပေါင်းလက်ကျန်")
def check_total_balance(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='income'", (user_id,))
    total_income = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='expense'", (user_id,))
    total_expense = cursor.fetchone()[0] or 0.0
    conn.close()
    
    current_cash = total_income - total_expense
    total_stock_val = get_total_stock_value(user_id)
    total_asset = current_cash + total_stock_val
    
    text = f"🏦 <b>စုစုပေါင်း ပိုင်ဆိုင်မှု အကျဉ်းချုပ်</b>\n\n"
    text += f"🟢 ဝင်ငွေ စုစုပေါင်း: {total_income:,.0f} Ks\n🔴 ထွက်ငွေ စုစုပေါင်း: {total_expense:,.0f} Ks\n---------------------------\n"
    text += f"💵 <b>လက်ရှိ ငွေသား (Cash):</b> {current_cash:,.0f} Ks\n📦 <b>လက်ရှိ Stock တန်ဖိုး:</b> {total_stock_val:,.0f} Ks\n=========================\n"
    text += f"💎 <b>စုစုပေါင်း ပိုင်ဆိုင်မှု (Cash + Stock): {total_asset:,.0f} Ks</b>"
    bot.send_message(message.chat.id, text, parse_mode="HTML")

# ----------------- 👥 အလုပ်သမား လစာမှတ်သည့်စနစ် -----------------
@bot.message_handler(func=lambda m: m.text == "👥 အလုပ်သမားလစာ")
def wages_menu(message):
    text = (
        "👥 <b>အလုပ်သမားလစာ စီမံခန့်ခွဲမှု</b>\n\n"
        "➕ <b>နေ့စဉ်လုပ်အားခ မှတ်ရန်:</b>\n<code>/wage [နာမည်] [ပမာဏ]</code>\n"
        "📋 <b>ပေးရန်ကျန် လစာစာရင်းကြည့်ရန်:</b>\n<code>/wages</code>\n"
        "📅 <b>လူတစ်ဦး၏ မှတ်တမ်းကြည့်ရန်:</b>\n<code>/wagelog [နာမည်]</code>\n"
        "💸 <b>လစာရှင်းပေးရန်:</b>\n<code>/paywage [နာမည်] [ပမာဏ]</code>\n"
        "❌ <b>မှားသွင်းမိသောလစာ ဖျက်ရန်:</b>\n<code>/delwage</code>"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=['wage'])
def log_wage(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            raise ValueError
        amount = float(parts[-1]) 
        name = " ".join(parts[1:-1]) 
        
        user_id = message.from_user.id
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO salaries (user_id, emp_name, amount) VALUES (?, ?, ?)", (user_id, name, amount))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ '{name}' အတွက် လုပ်အားခ {amount:,.0f} Ks ကို မှတ်သားထားပါပြီ။")
    except Exception:
        bot.reply_to(message, "⚠️ အသုံးပြုနည်း မှားယွင်းနေပါသည်။\nဥပမာ: <code>/wage Ko Ko 50000</code>", parse_mode="HTML")

@bot.message_handler(commands=['wages'])
def check_wages(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT emp_name, SUM(amount) FROM salaries WHERE user_id=? AND status='unpaid' GROUP BY emp_name", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        bot.reply_to(message, "👥 လစာပေးရန်ကျန်ရှိသူ မရှိသေးပါ။")
        return
        
    text = "👥 <b>ပေးရန်ကျန်ရှိသော လစာစာရင်းများ:</b>\n\n"
    for r in rows:
        if r[1] > 0:
            text += f"▪️ {r[0]} - {r[1]:,.0f} Ks\n"
        
    text += "\n💸 လစာရှင်းပေးလိုပါက <code>/paywage [နာမည်] [ပမာဏ]</code> ဟု ရိုက်ထည့်ပါ။"
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['wagelog'])
def view_wage_log(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            raise ValueError
        name = " ".join(parts[1:]) 
        user_id = message.from_user.id
        
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("SELECT amount, date, status FROM salaries WHERE user_id=? AND emp_name=? ORDER BY id DESC LIMIT 15", (user_id, name))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            bot.reply_to(message, f"⚠️ '{name}' အတွက် မှတ်တမ်းမရှိပါ။")
            return
            
        text = f"📋 <b>{name} ၏ လုပ်အားခ မှတ်တမ်း:</b>\n\n"
        for r in rows:
            amt, date_str, status = r[0], r[1].split()[0], r[2]
            if amt < 0:
                text += f"▪️ {date_str} : ရှင်းပေးငွေ/ထုတ်ငွေ {-amt:,.0f} Ks (✅)\n"
            else:
                status_icon = "✅" if status == 'paid' else "⏳"
                text += f"▪️ {date_str} : {amt:,.0f} Ks ({status_icon})\n"
        bot.reply_to(message, text, parse_mode="HTML")
    except:
         bot.reply_to(message, "⚠️ အသုံးပြုနည်း မှားယွင်းနေပါသည်။\nဥပမာ: <code>/wagelog Ko Ko</code>", parse_mode="HTML")

@bot.message_handler(commands=['paywage'])
def pay_wage(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "⚠️ အသုံးပြုနည်း မှားယွင်းနေပါသည်။\nဥပမာ: <code>/paywage Ko Ko 50000</code> (ပမာဏ သေချာထည့်ပါ)", parse_mode="HTML")
            return
            
        pay_amount = float(parts[-1]) 
        name = " ".join(parts[1:-1]) 
        user_id = message.from_user.id
        
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(amount) FROM salaries WHERE user_id=? AND emp_name=? AND status='unpaid'", (user_id, name))
        total_unpaid = cursor.fetchone()[0] or 0
        
        if total_unpaid <= 0:
            bot.reply_to(message, f"✅ '{name}' အတွက် ပေးရန်ကျန် လစာမရှိပါ။")
            conn.close()
            return
            
        if pay_amount > total_unpaid:
            bot.reply_to(message, f"⚠️ ပေးရန်ကျန်ငွေ ({total_unpaid:,.0f} Ks) ထက် ပိုနေပါသည်။")
            conn.close()
            return

        if pay_amount == total_unpaid:
            cursor.execute("UPDATE salaries SET status='paid' WHERE user_id=? AND emp_name=? AND status='unpaid'", (user_id, name))
        else:
            cursor.execute("INSERT INTO salaries (user_id, emp_name, amount, status) VALUES (?, ?, ?, 'unpaid')", (user_id, name, -pay_amount))
            
        cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'expense', ?, ?)", (user_id, pay_amount, f"{name} အား လစာရှင်းပေးခြင်း"))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ '{name}' အား လစာငွေ {pay_amount:,.0f} Ks ရှင်းပေးပြီးပါပြီ။\nလက်ကျန်ပေးရန်: {(total_unpaid - pay_amount):,.0f} Ks")
    except Exception:
        bot.reply_to(message, "⚠️ အသုံးပြုနည်း မှားယွင်းနေပါသည်။\nဥပမာ: <code>/paywage Ko Ko 50000</code>", parse_mode="HTML")

# ----------------- ❌ 👥 လစာစာရင်းဖျက်ခြင်း (Pagination) -----------------
def send_delete_wage_page(chat_id, user_id, page, message_id=None):
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM salaries WHERE user_id=? AND status='unpaid'", (user_id,))
    total = cursor.fetchone()[0]
    
    per_page = 5
    total_pages = (total + per_page - 1) // per_page
    cursor.execute("SELECT id, emp_name, amount, strftime('%Y-%m-%d', date) FROM salaries WHERE user_id=? AND status='unpaid' ORDER BY id DESC LIMIT ? OFFSET ?", (user_id, per_page, page * per_page))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows and page == 0:
        msg = "ဖျက်စရာ (မရှင်းရသေးသော) လစာစာရင်း မရှိသေးပါ။"
        if message_id: bot.edit_message_text(text=msg, chat_id=chat_id, message_id=message_id)
        else: bot.send_message(chat_id, msg)
        return
        
    items = [(w_id, f"👤 {emp_name}: {amount:,.0f} Ks [{date}]") for w_id, emp_name, amount, date in rows]
    markup = make_item_pagination_keyboard(items, "delwage", "page_delwage", page, total_pages)
    text = "👥 <b>မှားသွင်းမိသော လစာမှတ်တမ်းကို ရွေးချယ်ဖျက်ပါ</b> 👇"
    
    if message_id: bot.edit_message_text(text=text, chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode="HTML")
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(commands=['delwage'])
def delete_wage_menu(message):
    send_delete_wage_page(message.chat.id, message.from_user.id, 0)

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_delwage_"))
def handle_delwage_page(call):
    answer_cb(call.id)
    try:
        page = int(call.data.split("_")[2])
        send_delete_wage_page(call.message.chat.id, call.from_user.id, page, call.message.message_id)
    except Exception as e: print(e)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delwage_"))
def process_wage_delete(call):
    answer_cb(call.id, "ဖျက်နေပါသည်...")
    try:
        w_id = int(call.data.split("_")[1])
        with sqlite3.connect('accounting.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM salaries WHERE id=? AND user_id=?", (w_id, call.from_user.id))
            conn.commit()
        bot.edit_message_text(text="✅ ရွေးချယ်ထားသော လစာမှတ်တမ်းကို ဖျက်လိုက်ပါပြီ။", chat_id=call.message.chat.id, message_id=call.message.message_id)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"⚠️ ဖျက်ရာတွင် အမှားရှိနေပါသည်: {e}")

# ----------------- ❌ 💰 စာရင်းဖျက်ခြင်း (Pagination) -----------------
def send_delete_trans_page(chat_id, user_id, page, message_id=None):
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id=?", (user_id,))
    total = cursor.fetchone()[0]
    
    per_page = 5
    total_pages = (total + per_page - 1) // per_page
    cursor.execute("SELECT id, type, amount, note, strftime('%Y-%m-%d', date) FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (user_id, per_page, page * per_page))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows and page == 0:
        if message_id: bot.edit_message_text(text="ဖျက်စရာ ငွေကြေးစာရင်းမရှိသေးပါ။", chat_id=chat_id, message_id=message_id)
        else: bot.send_message(chat_id, "ဖျက်စရာ ငွေကြေးစာရင်းမရှိသေးပါ။")
        return
        
    items = []
    for r in rows:
        t_id, t_type, amount, note, date = r
        symbol = "🟢 +" if t_type == 'income' else "🔴 -"
        items.append((t_id, f"[{date[-5:]}] {symbol}{amount:,.0f} ({note[:15]})"))
        
    markup = make_item_pagination_keyboard(items, "deltrans", "page_deltrans", page, total_pages)
    text = "🗑 <b>ဖျက်လိုသော ငွေကြေးစာရင်းကို ရွေးချယ်ပါ</b> 👇"
    
    if message_id: bot.edit_message_text(text=text, chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode="HTML")
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "❌ စာရင်းဖျက်မည်")
def delete_menu(message):
    send_delete_trans_page(message.chat.id, message.from_user.id, 0)

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_deltrans_"))
def handle_deltrans_page(call):
    answer_cb(call.id)
    try:
        page = int(call.data.split("_")[2])
        send_delete_trans_page(call.message.chat.id, call.from_user.id, page, call.message.message_id)
    except Exception as e: print(e)

@bot.callback_query_handler(func=lambda call: call.data.startswith("deltrans_"))
def process_delete(call):
    answer_cb(call.id, "ဖျက်နေပါသည်...")
    try:
        t_id = int(call.data.split("_")[1])
        with sqlite3.connect('accounting.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (t_id, call.from_user.id))
            conn.commit()
        bot.edit_message_text(text="✅ ရွေးချယ်ထားသော စာရင်းကို ဖျက်လိုက်ပါပြီ။", chat_id=call.message.chat.id, message_id=call.message.message_id)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"⚠️ ဖျက်ရာတွင် အမှားရှိနေပါသည်: {e}")

# ----------------- ↩️ မှားသွားလျှင် ပြန်ဖျက်မည် Stock Undo (Pagination) -----------------
def send_undo_stock_page(chat_id, user_id, page, message_id=None):
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stock_logs WHERE user_id=?", (user_id,))
    total = cursor.fetchone()[0]
    
    per_page = 5
    total_pages = (total + per_page - 1) // per_page
    cursor.execute("SELECT id, action_type, item_name, qty, strftime('%Y-%m-%d', date) FROM stock_logs WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (user_id, per_page, page * per_page))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows and page == 0:
        if message_id: bot.edit_message_text(text="ဖျက်စရာ Stock မှတ်တမ်း မရှိသေးပါ။", chat_id=chat_id, message_id=message_id)
        else: bot.send_message(chat_id, "ဖျက်စရာ Stock မှတ်တမ်း မရှိသေးပါ။")
        return
        
    action_dict = {'buy': 'ဝယ်', 'sell': 'ရောင်း', 'old_stock': 'အဟောင်း', 'damage': 'အလျော့ပြ', 'borrow': 'ငှားယူ', 'return_borrow': 'ပြန်အပ်', 'lend': 'ငှားပေး', 'return_lend': 'ပြန်ရ'}
    
    items = []
    for r in rows:
        t_id, a_type, name, qty, date = r
        a_name = action_dict.get(a_type, a_type)
        items.append((t_id, f"[{date}] 📦 {name[:10]}: {qty} ခု ({a_name})"))
        
    markup = make_item_pagination_keyboard(items, "undostock", "page_undostock", page, total_pages)
    text = "↩️ <b>ဖျက်လိုသော Stock မှတ်တမ်းကို ရွေးချယ်ပါ</b> 👇\n(ငွေကြေးစာရင်းပါ ပြန်လည်ပြင်ဆင်ပေးပါမည်)"
    
    if message_id: bot.edit_message_text(text=text, chat_id=chat_id, message_id=message_id, reply_markup=markup, parse_mode="HTML")
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "↩️ မှားသွားလျှင် ပြန်ဖျက်မည်")
def undo_stock_menu(message):
    send_undo_stock_page(message.chat.id, message.from_user.id, 0)

@bot.callback_query_handler(func=lambda call: call.data.startswith("page_undostock_"))
def handle_undostock_page(call):
    answer_cb(call.id)
    try:
        page = int(call.data.split("_")[2])
        send_undo_stock_page(call.message.chat.id, call.from_user.id, page, call.message.message_id)
    except Exception as e: print(e)

@bot.callback_query_handler(func=lambda call: call.data.startswith("undostock_"))
def process_stock_undo(call):
    answer_cb(call.id, "ပြန်လည်ပြင်ဆင်နေပါသည်...")
    try:
        t_id = int(call.data.split("_")[1])
        user_id = call.from_user.id
        
        with sqlite3.connect('accounting.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT action_type, item_name, qty, trans_id, deli_trans_id FROM stock_logs WHERE id=? AND user_id=?", (t_id, user_id))
            log = cursor.fetchone()
            
            if log:
                a_type, name, qty, trans_id, deli_trans_id = log
                cursor.execute("SELECT id, quantity, rented_in, rented_out FROM inventory WHERE item_name=? AND user_id=?", (name, user_id))
                inv = cursor.fetchone()
                
                if inv:
                    inv_id, current_qty, r_in, r_out = inv
                    new_qty, new_r_in, new_r_out = current_qty, r_in, r_out
                    if a_type in ['buy', 'old_stock']: new_qty -= qty
                    elif a_type in ['sell', 'damage']: new_qty += qty
                    elif a_type == 'borrow': new_r_in -= qty
                    elif a_type == 'return_borrow': new_r_in += qty
                    elif a_type == 'lend': new_qty += qty; new_r_out -= qty
                    elif a_type == 'return_lend': new_qty -= qty; new_r_out += qty
                    cursor.execute("UPDATE inventory SET quantity=?, rented_in=?, rented_out=? WHERE id=?", (new_qty, new_r_in, new_r_out, inv_id))
                
                if trans_id: cursor.execute("DELETE FROM transactions WHERE id=?", (trans_id,))
                if deli_trans_id: cursor.execute("DELETE FROM transactions WHERE id=?", (deli_trans_id,))
                    
                cursor.execute("DELETE FROM stock_logs WHERE id=?", (t_id,))
                conn.commit()
                bot.edit_message_text(text="✅ ရွေးချယ်ထားသော Stock မှတ်တမ်းကို ဖျက်လိုက်ပါပြီ။", chat_id=call.message.chat.id, message_id=call.message.message_id)
            else:
                bot.edit_message_text(text="⚠️ မှတ်တမ်း ရှာမတွေ့ပါ။", chat_id=call.message.chat.id, message_id=call.message.message_id)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"⚠️ ဖျက်ရာတွင် အမှားရှိနေပါသည်: {e}")

# ----------------- 👑 ADMIN COMMANDS -----------------
@bot.message_handler(commands=['admin'])
def admin_panel_help(message):
    if message.from_user.id in ADMIN_IDS:
        text = (
            "👑 <b>Admin Commands List</b> 👑\n\n"
            "📢 <b>Broadcast:</b>\n<code>/broadcast [စာသား]</code>\n\n"
            "💾 <b>DB Manual Backup:</b>\n<code>/adminbackup</code>\n\n"
            "♻️ <b>DB Database Restore:</b>\n<code>/adminrestore</code>"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "⚠️ ဤလုပ်ဆောင်ချက်ကို Admin သာ အသုံးပြုနိုင်ပါသည်။")

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
    if message.from_user.id not in ADMIN_IDS: return
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.reply_to(message, "ပေးပို့လိုသော စာသားကို ရိုက်ထည့်ပါ။")
        return
    bot.send_message(message.chat.id, "⏳ Broadcast ပေးပို့နေပါသည်...")
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    success, failed = 0, 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 <b>Admin Announcement:</b>\n\n{text}", parse_mode="HTML")
            success += 1
        except: failed += 1
    bot.reply_to(message, f"✅ အောင်မြင်: {success}\n❌ မရသူ: {failed}")

@bot.message_handler(commands=['adminbackup'])
def admin_manual_backup(message):
    if message.from_user.id in ADMIN_IDS:
        try:
            if os.path.exists('accounting.db'):
                with open('accounting.db', 'rb') as f:
                    bot.send_document(message.chat.id, f, caption="👑 Admin Manual Backup (.db)")
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ Backup ယူရာတွင် အမှားဖြစ်နေပါသည်: {e}")

@bot.message_handler(commands=['adminrestore'])
def admin_restore_menu(message):
    if message.from_user.id in ADMIN_IDS:
        msg = bot.send_message(message.chat.id, "👑 **Admin DB Restore (.db)**\nကျေးဇူးပြု၍ `accounting.db` ဖိုင်ကို ပေးပို့ပါ။", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_restore)

def process_admin_restore(message):
    if is_cancel(message): return
    if message.document:
        try:
            if not message.document.file_name.endswith('.db'):
                bot.send_message(message.chat.id, "⚠️ .db ဖိုင်အမျိုးအစားကိုသာ လက်ခံပါသည်။")
                return
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with open('accounting.db', 'wb') as new_file: 
                new_file.write(downloaded_file)
            init_db() 
            bot.send_message(message.chat.id, "✅ Admin Restore အောင်မြင်ပါသည်။ Database အဟောင်းဖြင့် အစားထိုးပြီးပါပြီ။")
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ ဖိုင်ထည့်သွင်းရာတွင် အမှားရှိနေပါသည်: {e}")

# ----------------- 💾 Backup / Restore (Memory ပေါ်မှ တိုက်ရိုက်လုပ်ဆောင်ခြင်း) -----------------
@bot.message_handler(func=lambda m: m.text == "💾 Backup / Recover (Data)")
def backup_recover_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Excel ဖြင့် Backup ယူမည်", callback_data="backup_excel"),
        types.InlineKeyboardButton("♻️ Excel Restore လုပ်မည်", callback_data="restore_excel")
    )
    bot.send_message(message.chat.id, "သင်၏ ကိုယ်ပိုင် Data များကို Excel ဖြင့် သိမ်းဆည်းရန်နှင့် ပြန်လည်ထည့်သွင်းရန် ရွေးချယ်ပါ။", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["backup_excel", "restore_excel"])
def handle_backup_options(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    
    if call.data == "backup_excel":
        answer_cb(call.id, "Excel ဖိုင် ထုတ်ယူနေပါသည်...")
        bot.send_message(chat_id, "⏳ Excel ဖိုင် ဖန်တီးနေပါသည်။ ခဏစောင့်ပါ...")
        try:
            with sqlite3.connect('accounting.db') as conn:
                df_trans = pd.read_sql_query("SELECT * FROM transactions WHERE user_id=?", conn, params=(user_id,))
                df_inv = pd.read_sql_query("SELECT * FROM inventory WHERE user_id=?", conn, params=(user_id,))
                df_logs = pd.read_sql_query("SELECT * FROM stock_logs WHERE user_id=?", conn, params=(user_id,))
                df_salaries = pd.read_sql_query("SELECT * FROM salaries WHERE user_id=?", conn, params=(user_id,))
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_trans.to_excel(writer, sheet_name='Transactions', index=False)
                df_inv.to_excel(writer, sheet_name='Inventory', index=False)
                df_logs.to_excel(writer, sheet_name='StockLogs', index=False)
                df_salaries.to_excel(writer, sheet_name='Salaries', index=False)
            
            output.seek(0)
            output.name = f"Accounting_Backup_{datetime.now().strftime('%Y%m%d')}.xlsx" 
            
            bot.send_document(chat_id, document=output, caption="📊 သင့် Data များကို Excel ဖြင့် ထုတ်ယူပေးလိုက်ပါပြီ။")
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ Excel ထုတ်ယူရာတွင် အမှားရှိနေပါသည်: {e}")
        
    elif call.data == "restore_excel":
        answer_cb(call.id)
        msg = bot.send_message(chat_id, "ကျေးဇူးပြု၍ သင် Backup ယူထားသော <b>Excel (.xlsx)</b> ဖိုင်ကို ပေးပို့ပါ။\n⚠️ ယခင်ဒေတာများအပေါ်တွင် အစားထိုးမည်ဖြစ်သည်။", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_excel_recover)

def process_excel_recover(message):
    if is_cancel(message): return
    if not message.document:
        bot.send_message(message.chat.id, "⚠️ ဖိုင်မတွေ့ပါ။ လုပ်ဆောင်ချက်ကို ရပ်နားလိုက်ပါသည်။", reply_markup=main_menu())
        return
        
    try:
        if not message.document.file_name.endswith(('.xls', '.xlsx')):
            bot.send_message(message.chat.id, "⚠️ Excel (.xlsx) ဖိုင်ကိုသာ ထည့်သွင်းပါ။")
            return
        
        bot.send_message(message.chat.id, "⏳ Excel ဖိုင်ကို ဖတ်နေပါသည်... ခဏစောင့်ပါ။")
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_stream = io.BytesIO(downloaded_file)
        df_trans = pd.read_excel(file_stream, sheet_name='Transactions', engine='openpyxl')
        df_inv = pd.read_excel(file_stream, sheet_name='Inventory', engine='openpyxl')
        df_logs = pd.read_excel(file_stream, sheet_name='StockLogs', engine='openpyxl')
        df_salaries = pd.read_excel(file_stream, sheet_name='Salaries', engine='openpyxl')

        user_id = message.from_user.id
        
        with sqlite3.connect('accounting.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE user_id=?", (user_id,))
            cursor.execute("DELETE FROM inventory WHERE user_id=?", (user_id,))
            cursor.execute("DELETE FROM stock_logs WHERE user_id=?", (user_id,))
            cursor.execute("DELETE FROM salaries WHERE user_id=?", (user_id,))
            
            def safe_restore(df, table_name):
                if not df.empty:
                    if 'id' in df.columns:
                        df = df.drop(columns=['id'])
                    df['user_id'] = user_id
                    df.to_sql(table_name, conn, if_exists='append', index=False)

            safe_restore(df_trans, 'transactions')
            safe_restore(df_inv, 'inventory')
            safe_restore(df_logs, 'stock_logs')
            safe_restore(df_salaries, 'salaries')
            conn.commit()

        bot.send_message(message.chat.id, "✅ Excel ဖိုင်မှ Data များကို အောင်မြင်စွာ ပြန်လည်ထည့်သွင်း (Recover) ပြီးပါပြီ။", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ ဖိုင်ထည့်သွင်းရာတွင် အမှားအယွင်းရှိနေပါသည်။ Data မှားယွင်းနေပါသည်။\nError: {e}", reply_markup=main_menu())

# ----------------- Reset / Cancel Handlers -----------------
@bot.callback_query_handler(func=lambda call: call.data == "cancel_reset")
def cancel_action(call):
    answer_cb(call.id)
    try:
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    except: pass

@bot.message_handler(func=lambda m: m.text == "🔄 အသစ်ပြန်စမည်")
def reset_confirm(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ အားလုံးဖျက်မည်", callback_data="confirm_reset"), types.InlineKeyboardButton("✖️ မလုပ်တော့ပါ", callback_data="cancel_reset"))
    bot.send_message(message.chat.id, "⚠️ **သတိပေးချက်:**\nငွေကြေး၊ ပစ္စည်း(Stock) နှင့် လစာ မှတ်တမ်းများ အားလုံး ပျက်သွားမည်ဖြစ်သည်။", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "confirm_reset")
def do_reset(call):
    answer_cb(call.id, "ဖျက်နေပါသည်...")
    try:
        user_id = call.from_user.id
        with sqlite3.connect('accounting.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE user_id=?", (user_id,))
            cursor.execute("DELETE FROM inventory WHERE user_id=?", (user_id,))
            cursor.execute("DELETE FROM stock_logs WHERE user_id=?", (user_id,))
            cursor.execute("DELETE FROM salaries WHERE user_id=?", (user_id,))
            conn.commit()
        bot.edit_message_text(text="✅ မှတ်တမ်းအားလုံးကို အောင်မြင်စွာ ဖျက်လိုက်ပါပြီ။", chat_id=call.message.chat.id, message_id=call.message.message_id)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"⚠️ ဖျက်ရာတွင် အမှားရှိနေပါသည်: {e}")

if __name__ == '__main__':
    sync_db_from_mongo()
    init_db()
    keep_alive()
    
    try:
        bot.remove_webhook()
        time.sleep(1) # Webhook သေချာပြုတ်ရန် အနည်းငယ်စောင့်ခြင်း
        print("Webhook removed automatically to prevent Error 409.")
    except:
        pass
        
    print("Bot is running perfectly with MongoDB Cloud Sync & Safe Callbacks...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
