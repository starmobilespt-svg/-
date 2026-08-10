import sqlite3
import telebot
from telebot import types
import os
from flask import Flask
from threading import Thread

# ----------------- Ping အတွက် Web Server Setup -----------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_server)
    t.start()
# -----------------------------------------------------------------

TOKEN = "8580240882:AAHVaMF1a9E_LyFJgLCEhdTomHgUBB-ijnI"
bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            note TEXT,
            date TIMESTAMP DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            quantity INTEGER DEFAULT 0,
            buy_price REAL DEFAULT 0,
            sell_price REAL DEFAULT 0
        )
    ''')
    # Stock အမှားပြင်ဆင်ရန်အတွက် Log Table အသစ်
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT,
            item_name TEXT,
            qty INTEGER,
            trans_id INTEGER,
            date TIMESTAMP DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    
    try:
        cursor.execute('ALTER TABLE inventory ADD COLUMN rented_out INTEGER DEFAULT 0')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE inventory ADD COLUMN rented_in INTEGER DEFAULT 0')
    except:
        pass

    conn.commit()
    conn.close()

init_db()

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
    
    if not rows:
        return "📦 <i>ပြသရန် Stock မရှိသေးပါ။</i>\n\n"
        
    text = "📦 <b>ရွေးချယ်နိုင်သော Stock များ:</b>\n(အမည်ကို နှိပ်၍ Copy ကူးပါ)\n"
    for r in rows:
        text += f"▪️ <code>{r[0]}</code> - (လက်ကျန်: {r[1]} ခု)\n"
    text += "\n"
    return text

# ----------------- Menus -----------------
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("➕ ဝင်ငွေမှတ်မည်"), types.KeyboardButton("➖ ထွက်ငွေမှတ်မည်"))
    markup.add(types.KeyboardButton("📅 ဒီနေ့စာရင်း"), types.KeyboardButton("🗓 ဒီလစာရင်း"))
    markup.add(types.KeyboardButton("💰 စုစုပေါင်းလက်ကျန်"), types.KeyboardButton("ဝယ်/ရောင်း/ငှား/stock"))
    markup.add(types.KeyboardButton("💾 Backup ယူမည်"), types.KeyboardButton("♻️ Recover လုပ်မည်"))
    markup.add(types.KeyboardButton("❌ စာရင်းဖျက်မည်"), types.KeyboardButton("🔄 အသစ်ပြန်စမည်"))
    return markup

def stock_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("🛒 ဝယ်မည် (Buy)"), types.KeyboardButton("🛍 ရောင်းမည် (Sell)"))
    markup.add(types.KeyboardButton("📦 Stock အဟောင်းသွင်းမည်"), types.KeyboardButton("🗑 ပျက်စီး/အလျော့ပြ"))
    markup.add(types.KeyboardButton("🔄 အငှားကဏ္ဍ (Rentals)"), types.KeyboardButton("📊 Stock တန်ဖိုး/လက်ကျန်"))
    # မှားသွားရင်ပြန်ဖျက်မည့် ခလုတ်အသစ်
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
    text = "မင်္ဂလာပါ! စာရင်းကိုင်နှင့် Stock Bot မှ ကြိုဆိုပါတယ်။\nအောက်ပါ ခလုတ်များကို နှိပ်၍ အသုံးပြုနိုင်ပါသည်။"
    bot.send_message(message.chat.id, text, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 ပင်မမီနူးသို့")
def back_to_main(message):
    bot.send_message(message.chat.id, "ပင်မမီနူးသို့ ပြန်ရောက်ပါပြီ။", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 Stock မီနူးသို့")
def back_to_stock(message):
    bot.send_message(message.chat.id, "📦 Stock မီနူးသို့ ပြန်ရောက်ပါပြီ။", reply_markup=stock_menu())

@bot.message_handler(func=lambda m: m.text == "ဝယ်/ရောင်း/ငှား/stock")
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

# ----------------- STOCK (ဝယ် / ရောင်း / အဟောင်းသွင်း / ပျက်စီး) -----------------

@bot.message_handler(func=lambda m: m.text == "🛒 ဝယ်မည် (Buy)")
def ask_buy_stock(message):
    stock_list = get_available_stock_html(message.from_user.id, "all")
    msg = bot.send_message(message.chat.id, stock_list + "ဝယ်ယူမည့် ပစ္စည်းအမည်၊ အရေအတွက် နှင့် ဝယ်ဈေး(တစ်ခုစာ) ကို ကော်မာ (,) ခြား၍ ရိုက်ထည့်ပါ။\n\nဥပမာ: <code>ဖုန်း, 5, 100000</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_buy_stock)

def process_buy_stock(message):
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name = parts[0]
        qty = int(parts[1])
        buy_price = float(parts[2])
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
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity, buy_price) VALUES (?, ?, ?, ?)", 
                           (user_id, name, qty, buy_price))
            
        cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'expense', ?, ?)",
                       (user_id, total_expense, f"{name} ဝယ်ယူခြင်း"))
        trans_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id) VALUES (?, 'buy', ?, ?, ?)", (user_id, name, qty, trans_id))

        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"✅ ဝယ်ယူမှုမှတ်တမ်း တင်ပြီးပါပြီ။\n\nပစ္စည်း: {name}\nအဝယ်အရေအတွက်: {qty}\nစုစုပေါင်းကျသင့်ငွေ: {total_expense:,.0f} Ks\n📦 ယခု Stock လက်ကျန်: {new_qty} ခု", reply_markup=stock_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။", reply_markup=stock_menu())

@bot.message_handler(func=lambda m: m.text == "📦 Stock အဟောင်းသွင်းမည်")
def ask_old_stock(message):
    stock_list = get_available_stock_html(message.from_user.id, "all")
    msg = bot.send_message(message.chat.id, stock_list + "ယခင်ရှိပြီးသား Stock အဟောင်းများ ထည့်သွင်းရန် (ငွေကြေးစာရင်း မထိခိုက်ပါ)\n\nပစ္စည်းအမည်၊ အရေအတွက် နှင့် ဝယ်ဈေး(တစ်ခုစာ) ကို ကော်မာ (,) ခြား၍ ရိုက်ထည့်ပါ။\n\nဥပမာ: <code>ဖုန်း, 5, 100000</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_old_stock)

def process_old_stock(message):
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name = parts[0]
        qty = int(parts[1])
        buy_price = float(parts[2])
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
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity, buy_price) VALUES (?, ?, ?, ?)", 
                           (user_id, name, qty, buy_price))
            
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id) VALUES (?, 'old_stock', ?, ?, NULL)", (user_id, name, qty))

        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ Stock အဟောင်း ထည့်သွင်းခြင်း အောင်မြင်ပါသည်။\n\nပစ္စည်း: {name}\nအရေအတွက်: +{qty}\n📦 ယခု Stock လက်ကျန်: {new_qty} ခု", reply_markup=stock_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။", reply_markup=stock_menu())

@bot.message_handler(func=lambda m: m.text == "🛍 ရောင်းမည် (Sell)")
def ask_sell_stock(message):
    stock_list = get_available_stock_html(message.from_user.id, "quantity > 0")
    msg = bot.send_message(message.chat.id, stock_list + "ရောင်းမည့် ပစ္စည်းအမည်၊ အရေအတွက် နှင့် ရောင်းဈေး(တစ်ခုစာ) ကို ကော်မာ (,) ခြား၍ ရိုက်ပါ။\n\nဥပမာ: <code>ဖုန်း, 2, 150000</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_sell_stock)

def process_sell_stock(message):
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name = parts[0]
        qty = int(parts[1])
        sell_price = float(parts[2])
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
        cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'income', ?, ?)",
                       (user_id, total_income, f"{name} ရောင်းရငွေ"))
        trans_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id) VALUES (?, 'sell', ?, ?, ?)", (user_id, name, qty, trans_id))

        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"✅ ရောင်းချမှု အောင်မြင်ပါသည်။\n\nပစ္စည်း: {name} ({qty} ခု)\nစုစုပေါင်းရငွေ: {total_income:,.0f} Ks\n📦 ယခု Stock လက်ကျန်: {new_qty} ခု", reply_markup=stock_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။", reply_markup=stock_menu())

@bot.message_handler(func=lambda m: m.text == "🗑 ပျက်စီး/အလျော့ပြ")
def ask_damage_stock(message):
    stock_list = get_available_stock_html(message.from_user.id, "quantity > 0")
    msg = bot.send_message(message.chat.id, stock_list + "ပျက်စီး/ပျောက်ဆုံးသွားသော ပစ္စည်းအမည် နှင့် အရေအတွက်ကို ကော်မာ (,) ခြား၍ ရိုက်ပါ။\n\nဥပမာ: <code>ဖုန်း, 1</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_damage_stock)

def process_damage_stock(message):
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name = parts[0]
        qty = int(parts[1])
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
        
        cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id) VALUES (?, 'damage', ?, ?, NULL)", (user_id, name, qty))

        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"🗑 {name} ({qty} ခု) စာရင်းမှ ပယ်ဖျက်လိုက်ပါပြီ။\n📦 ယခု Stock လက်ကျန်: {new_qty} ခု", reply_markup=stock_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။", reply_markup=stock_menu())


# ----------------- RENTAL (အငှားကဏ္ဍ) -----------------
@bot.message_handler(func=lambda m: m.text == "📥 အငှားယူမည် (Borrow)")
def ask_rent_in(message):
    stock_list = get_available_stock_html(message.from_user.id, "all")
    msg = bot.send_message(message.chat.id, stock_list + "သူများဆီမှ အငှားယူမည့် ပစ္စည်းအမည် နှင့် အရေအတွက်ကို ရိုက်ပါ။\n\nဥပမာ: <code>စက်ဘီး, 2</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_renting, "borrow")

@bot.message_handler(func=lambda m: m.text == "📤 အငှားပြန်အပ်မည်")
def ask_return_borrow(message):
    stock_list = get_available_stock_html(message.from_user.id, "rented_in > 0")
    msg = bot.send_message(message.chat.id, stock_list + "ပြန်အပ်မည့် ပစ္စည်းအမည်၊ အရေအတွက် နှင့် ပေးရမည့်ငှားခ(စုစုပေါင်း) ကို ရိုက်ပါ။ (ငှားခမပေးရပါက 0 ဟုထည့်ပါ)\n\nဥပမာ: <code>စက်ဘီး, 2, 5000</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_renting, "return_borrow")

@bot.message_handler(func=lambda m: m.text == "📤 အငှားပေးမည် (Lend)")
def ask_rent_out(message):
    stock_list = get_available_stock_html(message.from_user.id, "quantity > 0")
    msg = bot.send_message(message.chat.id, stock_list + "အခြားသူအား အငှားပေးမည့် ပစ္စည်းအမည် နှင့် အရေအတွက် ကိုရိုက်ပါ။\n\nဥပမာ: <code>စက်ဘီး, 1</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_renting, "lend")

@bot.message_handler(func=lambda m: m.text == "📥 အငှားပြန်ရမည်")
def ask_return_lend(message):
    stock_list = get_available_stock_html(message.from_user.id, "rented_out > 0")
    msg = bot.send_message(message.chat.id, stock_list + "ပြန်ရမည့် ပစ္စည်းအမည်၊ အရေအတွက် နှင့် ရမည့်ငှားခ(စုစုပေါင်း) ကို ရိုက်ပါ။ (ငှားခမရပါက 0 ဟုထည့်ပါ)\n\nဥပမာ: <code>စက်ဘီး, 1, 3000</code>", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_renting, "return_lend")

def process_renting(message, action):
    try:
        parts = [p.strip() for p in message.text.split(',')]
        name = parts[0]
        qty = int(parts[1])
        fee = float(parts[2]) if len(parts) > 2 else 0.0
        user_id = message.from_user.id
        
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, quantity, rented_in, rented_out FROM inventory WHERE user_id=? AND item_name=?", (user_id, name))
        row = cursor.fetchone()
        
        if not row and action in ["return_borrow", "lend", "return_lend"]:
            bot.send_message(message.chat.id, "⚠️ ထိုပစ္စည်းစာရင်းတွင်မရှိပါ။", reply_markup=rent_menu())
            conn.close()
            return

        if not row and action == "borrow":
            cursor.execute("INSERT INTO inventory (user_id, item_name, quantity, rented_in, rented_out) VALUES (?, ?, 0, ?, 0)", (user_id, name, qty))
            cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id) VALUES (?, 'borrow', ?, ?, NULL)", (user_id, name, qty))
            conn.commit()
            bot.send_message(message.chat.id, f"📥 '{name}' ({qty} ခု) သူများဆီမှ အငှားယူစာရင်း သွင်းပြီးပါပြီ။", reply_markup=rent_menu())
            conn.close()
            return
            
        item_id, current_qty, r_in, r_out = row
        trans_id = None
        
        if action == "borrow":
            cursor.execute("UPDATE inventory SET rented_in=? WHERE id=?", (r_in + qty, item_id))
            cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id) VALUES (?, 'borrow', ?, ?, NULL)", (user_id, name, qty))
            bot.send_message(message.chat.id, f"📥 '{name}' ({qty} ခု) သူများဆီမှ အငှားယူစာရင်း သွင်းပြီးပါပြီ။", reply_markup=rent_menu())
            
        elif action == "return_borrow":
            if r_in < qty:
                bot.send_message(message.chat.id, "⚠️ အငှားယူထားသော အရေအတွက်ထက် ကျော်လွန်နေပါသည်။", reply_markup=rent_menu())
                return
            cursor.execute("UPDATE inventory SET rented_in=? WHERE id=?", (r_in - qty, item_id))
            if fee > 0:
                cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'expense', ?, ?)", (user_id, fee, f"{name} ငှားခပေးငွေ"))
                trans_id = cursor.lastrowid
            cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id) VALUES (?, 'return_borrow', ?, ?, ?)", (user_id, name, qty, trans_id))
            bot.send_message(message.chat.id, f"📤 '{name}' ({qty} ခု) အငှားပြန်အပ်ပြီးပါပြီ။\n{'🔴 ငှားခပေးငွေ (ထွက်ငွေ): ' + str(fee) + ' Ks' if fee > 0 else ''}", reply_markup=rent_menu())
            
        elif action == "lend":
            if current_qty < qty:
                bot.send_message(message.chat.id, "⚠️ သင့်ထံတွင် အငှားပေးရန် လက်ရှိ Stock အလုံအလောက်မရှိပါ။", reply_markup=rent_menu())
                return
            cursor.execute("UPDATE inventory SET quantity=?, rented_out=? WHERE id=?", (current_qty - qty, r_out + qty, item_id))
            cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id) VALUES (?, 'lend', ?, ?, NULL)", (user_id, name, qty))
            bot.send_message(message.chat.id, f"📤 '{name}' ({qty} ခု) သူများအား အငှားပေးလိုက်ပါပြီ။\n📦 လက်ရှိကျန်သော Stock: {current_qty - qty} ခု", reply_markup=rent_menu())
            
        elif action == "return_lend":
            if r_out < qty:
                bot.send_message(message.chat.id, "⚠️ အငှားပေးထားသော အရေအတွက်ထက် ကျော်လွန်နေပါသည်။", reply_markup=rent_menu())
                return
            cursor.execute("UPDATE inventory SET quantity=?, rented_out=? WHERE id=?", (current_qty + qty, r_out - qty, item_id))
            if fee > 0:
                cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, 'income', ?, ?)", (user_id, fee, f"{name} ငှားခရငွေ"))
                trans_id = cursor.lastrowid
            cursor.execute("INSERT INTO stock_logs (user_id, action_type, item_name, qty, trans_id) VALUES (?, 'return_lend', ?, ?, ?)", (user_id, name, qty, trans_id))
            bot.send_message(message.chat.id, f"📥 '{name}' ({qty} ခု) အငှားပြန်လည်ရရှိပါပြီ။\n{'🟢 ငှားခရငွေ (ဝင်ငွေ): ' + str(fee) + ' Ks' if fee > 0 else ''}", reply_markup=rent_menu())

        conn.commit()
        conn.close()
    except Exception:
        bot.send_message(message.chat.id, "⚠️ Format မှားယွင်းနေပါသည်။", reply_markup=rent_menu())

# ----------------- ⚠️ မှားသွားလျှင် ပြန်ဖျက်မည် (Undo Stock) -----------------
@bot.message_handler(func=lambda m: m.text == "↩️ မှားသွားလျှင် ပြန်ဖျက်မည်")
def undo_stock_menu(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, action_type, item_name, qty, strftime('%Y-%m-%d', date) FROM stock_logs WHERE user_id=? ORDER BY id DESC LIMIT 5", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "ဖျက်စရာ မှတ်တမ်း မရှိသေးပါ။")
        return

    action_dict = {
        'buy': 'ဝယ်ယူမှု',
        'sell': 'ရောင်းချမှု',
        'old_stock': 'အဟောင်းသွင်းမှု',
        'damage': 'အလျော့ပြမှု',
        'borrow': 'အငှားယူမှု',
        'return_borrow': 'အငှားပြန်အပ်မှု',
        'lend': 'အငှားပေးမှု',
        'return_lend': 'အငှားပြန်ရမှု'
    }

    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        t_id, a_type, name, qty, date = r
        a_name = action_dict.get(a_type, a_type)
        btn_text = f"[{date}] {name}: {qty} ခု ({a_name})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"undostock_{t_id}"))
    
    markup.add(types.InlineKeyboardButton("ပယ်ဖျက်မည်", callback_data="cancel_reset"))
    bot.send_message(message.chat.id, "ဖျက်လိုသော Stock လုပ်ဆောင်ချက်ကို ရွေးချယ်ပါ (နောက်ဆုံး ၅ ခု) -\n(မှတ်ချက် - ဝယ်/ရောင်း/ငှားခ ငွေကြေးစာရင်းများပါ အလိုအလျောက် ပယ်ဖျက်ပေးမည်)", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("undostock_"))
def process_stock_undo(call):
    t_id = call.data.split("_")[1]
    user_id = call.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT action_type, item_name, qty, trans_id FROM stock_logs WHERE id=? AND user_id=?", (t_id, user_id))
    log = cursor.fetchone()
    
    if log:
        a_type, name, qty, trans_id = log
        cursor.execute("SELECT id, quantity, rented_in, rented_out FROM inventory WHERE item_name=? AND user_id=?", (name, user_id))
        inv = cursor.fetchone()
        
        if inv:
            inv_id, current_qty, r_in, r_out = inv
            new_qty, new_r_in, new_r_out = current_qty, r_in, r_out
            
            # Revert logic
            if a_type in ['buy', 'old_stock']:
                new_qty -= qty
            elif a_type in ['sell', 'damage']:
                new_qty += qty
            elif a_type == 'borrow':
                new_r_in -= qty
            elif a_type == 'return_borrow':
                new_r_in += qty
            elif a_type == 'lend':
                new_qty += qty
                new_r_out -= qty
            elif a_type == 'return_lend':
                new_qty -= qty
                new_r_out += qty
                
            # Update Database
            cursor.execute("UPDATE inventory SET quantity=?, rented_in=?, rented_out=? WHERE id=?", (new_qty, new_r_in, new_r_out, inv_id))
        
        # Financial Transaction တွဲပါလာခဲ့လျှင် အဲ့ဒါကိုပါ ဖြတ်မည်
        if trans_id:
            cursor.execute("DELETE FROM transactions WHERE id=?", (trans_id,))
            
        cursor.execute("DELETE FROM stock_logs WHERE id=?", (t_id,))
        conn.commit()
        bot.edit_message_text("✅ ရွေးချယ်ထားသော Stock မှတ်တမ်းကို ဖျက်လိုက်ပါပြီ။ (အရေအတွက်နှင့် ငွေကြေးစာရင်းများ မူလအတိုင်း ပြန်ဖြစ်သွားပါမည်)", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("⚠️ မှတ်တမ်း ရှာမတွေ့ပါ။", call.message.chat.id, call.message.message_id)
    conn.close()

# ----------------- 📊 Stock Valuation (တန်ဖိုးတွက်ချက်ခြင်း) -----------------
@bot.message_handler(func=lambda m: m.text == "📊 Stock တန်ဖိုး/လက်ကျန်")
def check_stock_value(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity, rented_out, rented_in, buy_price FROM inventory WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        bot.send_message(message.chat.id, "📦 ပစ္စည်း (Stock) စာရင်း အလွတ်ဖြစ်နေပါသည်။")
        return
        
    text = "📊 <b>Stock လက်ကျန်နှင့် တန်ဖိုး</b>\n=========================\n\n"
    grand_total_value = 0
    
    for r in rows:
        name, qty, r_out, r_in, buy_price = r
        owned_total = qty + r_out 
        item_value = owned_total * buy_price
        grand_total_value += item_value
        
        if owned_total > 0 or r_in > 0:
            text += f"▪️ <b>{name}</b>\n"
            text += f"   📦 (လက်ရှိ {qty} + ငှားထား {r_out}) = <b>{owned_total} ခု</b>\n"
            if r_in > 0:
                text += f"   ⚠️ <i>သူများဆီမှ အငှားယူထားသော: {r_in} ခု</i>\n"
            text += f"   💰 တန်ဖိုး: {owned_total} x {buy_price:,.0f} = <b>{item_value:,.0f} Ks</b>\n\n"
        
    text += f"=========================\n"
    text += f"🏆 <b>စုစုပေါင်း Stock တန်ဖိုး: {grand_total_value:,.0f} Ks</b>"
        
    bot.send_message(message.chat.id, text, parse_mode="HTML")

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
    
    total_inc = total_inc or 0.0
    total_exp = total_exp or 0.0
    
    text = "🗓 <b>ဒီလ ဘဏ္ဍာရေး အစီရင်ခံစာ (အကျဉ်းချုပ်)</b>\n=========================\n\n"
    
    if incomes:
        text += "🟢 <b>ဝင်ငွေ ခေါင်းစဉ်များ:</b>\n"
        for note, amt in incomes:
            text += f"▪️ {note}: {amt:,.0f} Ks\n"
        text += "\n"
        
    if expenses:
        text += "🔴 <b>ထွက်ငွေ ခေါင်းစဉ်များ:</b>\n"
        for note, amt in expenses:
            text += f"▪️ {note}: {amt:,.0f} Ks\n"
        text += "\n"
        
    if not incomes and not expenses:
        text += "<i>ဒီလအတွက် မှတ်တမ်း မရှိသေးပါ။</i>\n\n"
        
    text += "=========================\n"
    text += f"🟢 <b>ဝင်ငွေစုစုပေါင်း:</b> {total_inc:,.0f} Ks\n"
    text += f"🔴 <b>ထွက်ငွေစုစုပေါင်း:</b> {total_exp:,.0f} Ks\n"
    text += f"💰 <b>ဒီလ ပိုငွေ (Net):</b> {(total_inc - total_exp):,.0f} Ks"
    
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
    
    text = f"🏦 စုစုပေါင်း ငွေကြေးစာရင်းချုပ်\n\n🟢 ဝင်ငွေ: {total_income:,.0f} Ks\n🔴 ထွက်ငွေ: {total_expense:,.0f} Ks\n---------------------------\n💰 လက်ရှိကျန်ငွေ: {(total_income - total_expense):,.0f} Ks"
    bot.send_message(message.chat.id, text)

# ----------------- Backup နှင့် Recover -----------------
@bot.message_handler(func=lambda m: m.text == "💾 Backup ယူမည်")
def backup_db(message):
    if os.path.exists('accounting.db'):
        with open('accounting.db', 'rb') as f:
            bot.send_document(message.chat.id, f, caption="💾 Database Backup ဖိုင် ရပါပြီ။\n(ငွေကြေး၊ Stock၊ အငှားမှတ်တမ်း အားလုံးပါဝင်ပါသည်။)")
    else:
        bot.send_message(message.chat.id, "Database ဖိုင် မတွေ့ပါ။")

@bot.message_handler(func=lambda m: m.text == "♻️ Recover လုပ်မည်")
def start_recover(message):
    msg = bot.send_message(message.chat.id, "ကျေးဇူးပြု၍ သင် Backup ယူထားသော **accounting.db** ဖိုင်ကို ပေးပို့ပါ။", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_recover)

def process_recover(message):
    if message.document:
        try:
            file_name = message.document.file_name
            if not file_name.endswith('.db'):
                bot.send_message(message.chat.id, "⚠️ .db ဖိုင်ကိုသာ ထည့်သွင်းပါ။", reply_markup=main_menu())
                return
                
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            with open('accounting.db', 'wb') as new_file:
                new_file.write(downloaded_file)
                
            init_db() 
                
            bot.send_message(message.chat.id, "✅ Data အဟောင်းများကို အောင်မြင်စွာ ပြန်လည်ထည့်သွင်း (Recover) ပြီးပါပြီ။", reply_markup=main_menu())
        except Exception:
            bot.send_message(message.chat.id, "⚠️ ဖိုင်ထည့်သွင်းရာတွင် အမှားအယွင်းရှိနေပါသည်။", reply_markup=main_menu())

# ----------------- စာရင်းဖျက်ခြင်း နှင့် အသစ်ပြန်စခြင်း -----------------
@bot.message_handler(func=lambda m: m.text == "❌ စာရင်းဖျက်မည်")
def delete_menu(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, amount, note, strftime('%Y-%m-%d', date) FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 5", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "ဖျက်စရာ ငွေကြေးစာရင်းမရှိသေးပါ။")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        t_id, t_type, amount, note, date = r
        symbol = "+" if t_type == 'income' else "-"
        btn_text = f"[{date}] {symbol}{amount:,.0f} ({note})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"del_{t_id}"))
    
    markup.add(types.InlineKeyboardButton("ပယ်ဖျက်မည်", callback_data="cancel_reset"))
    bot.send_message(message.chat.id, "ဖျက်လိုသော ငွေကြေးစာရင်းကို ရွေးချယ်ပါ (နောက်ဆုံးသွင်း ၅ ခု) -", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def process_delete(call):
    t_id = call.data.split("_")[1]
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (t_id, call.from_user.id))
    conn.commit()
    conn.close()
    bot.edit_message_text("✅ ရွေးချယ်ထားသော စာရင်းကို ဖျက်လိုက်ပါပြီ။", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "🔄 အသစ်ပြန်စမည်")
def reset_confirm(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ အားလုံးဖျက်မည်", callback_data="confirm_reset"), types.InlineKeyboardButton("❌ မဖျက်တော့ပါ", callback_data="cancel_reset"))
    bot.send_message(message.chat.id, "⚠️ **သတိပေးချက်:**\nငွေကြေးစာရင်းများနှင့် ပစ္စည်း(Stock)/အငှား မှတ်တမ်းများ အားလုံး ပျက်သွားမည်ဖြစ်သည်။", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_reset", "cancel_reset"])
def handle_reset_choice(call):
    if call.data == "confirm_reset":
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE user_id=?", (call.from_user.id,))
        cursor.execute("DELETE FROM inventory WHERE user_id=?", (call.from_user.id,))
        cursor.execute("DELETE FROM stock_logs WHERE user_id=?", (call.from_user.id,))
        conn.commit()
        conn.close()
        bot.edit_message_text("✅ မှတ်တမ်းအားလုံးကို အောင်မြင်စွာ ဖျက်လိုက်ပါပြီ။", call.message.chat.id, call.message.message_id)
    elif call.data == "cancel_reset":
        bot.edit_message_text("❌ လုပ်ဆောင်ချက်ကို ပယ်ဖျက်လိုက်ပါသည်။", call.message.chat.id, call.message.message_id)

if __name__ == '__main__':
    keep_alive()
    print("Bot is running with Stock Undo feature...")
    bot.infinity_polling()
