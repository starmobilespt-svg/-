import sqlite3
import telebot
from telebot import types
import csv
import io
import os

TOKEN = "8580240882:AAHJYpwlC5adLcdxXZIOa5XDL80Xj7Jvg9s"
bot = telebot.TeleBot(TOKEN)

# 📢 သင့်ရဲ့ Telegram Channel ကို ထည့်သွင်းထားပါသည်
CHANNEL_USERNAME = "@starmobile63956"

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
    conn.commit()
    conn.close()

init_db()

# --- Channel Join စစ်ဆေးသည့် Function နှင့် Decorator ---
def check_user_channel(bot_instance, user_id):
    try:
        member = bot_instance.get_chat_member(CHANNEL_USERNAME, user_id)
        active_statuses = ["creator", "administrator", "member"]
        if member.status in active_statuses:
            return True
        return False
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False

def check_channel(func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        if not check_user_channel(bot, user_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 Channel Joinရန်", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
            markup.add(types.InlineKeyboardButton("🔄 ပြန်စစ်မည်", callback_data="check_subscription"))
            bot.send_message(
                message.chat.id, 
                "⚠️ **လုပ်ဆောင်ချက် မအောင်မြင်ပါ!**\n\nကျေးဇူးပြု၍ ကျွန်ုပ်တို့၏ Channel ကို အရင် Join ပေးပါ။ ပြီးမှ အောက်ပါ 'ပြန်စစ်မည်' ခလုတ်ကို နှိပ်၍ အသုံးပြုပါ။", 
                reply_markup=markup,
                parse_mode="Markdown"
            )
            return
        return func(message, *args, **kwargs)
    return wrapper

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def verify_subscription(call):
    if check_user_channel(bot, call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Channel Joinပြီးပါပြီ။ Bot ကို ဆက်လက်သုံးနိုင်ပါပြီ။")
        bot.edit_message_text(
            "✅ ကျေးဇူးတင်ပါတယ်! Channel Join ပြီးဖြစ်သောကြောင့် Bot ကို အောင်မြင်စွာ အသုံးပြုနိုင်ပါပြီ။ \n\nစတင်ရန် /start ကို နှိပ်ပါ။", 
            call.message.chat.id, 
            call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "❌ သင် Channel မ join ရသေးပါ။ ကျေးဇူးပြု၍ အရင် Join ပေးပါ။", show_alert=True)

# ----------------------------------------------------

def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("➕ ဝင်ငွေမှတ်မည်"), types.KeyboardButton("➖ ထွက်ငွေမှတ်မည်"))
    markup.add(types.KeyboardButton("📅 ဒီနေ့စာရင်း"), types.KeyboardButton("🗓 ဒီလစာရင်း"))
    markup.add(types.KeyboardButton("💰 စုစုပေါင်းလက်ကျန်"), types.KeyboardButton("❌ စာရင်းဖျက်မည်"))
    markup.add(types.KeyboardButton("📥 Excel ထုတ်မည်"), types.KeyboardButton("💾 Backup ယူမည်"))
    markup.add(types.KeyboardButton("🔄 စာရင်းအသစ်ပြန်စမည်"))
    return markup

@bot.message_handler(commands=['start'])
@check_channel
def send_welcome(message):
    text = "မင်္ဂလာပါ! စာရင်းကိုင် Bot မှ ကြိုဆိုပါတယ်။\nအောက်ပါ ခလုတ်များကို နှိပ်၍ အသုံးပြုနိုင်ပါသည်။"
    bot.send_message(message.chat.id, text, reply_markup=main_menu())

# ----------------- စာရင်းမှတ်ခြင်း -----------------
@bot.message_handler(func=lambda m: m.text in ["➕ ဝင်ငွေမှတ်မည်", "➖ ထွက်ငွေမှတ်မည်"])
@check_channel
def start_transaction(message):
    trans_type = 'income' if 'ဝင်ငွေ' in message.text else 'expense'
    msg = bot.send_message(message.chat.id, "ပမာဏနှင့် အကြောင်းအရာကို ရိုက်ထည့်ပါ\n(ဥပမာ - 5000 လစာ သို့မဟုတ် 1500 မနက်စာ):")
    bot.register_next_step_handler(msg, process_transaction, trans_type)

def process_transaction(message, trans_type):
    try:
        parts = message.text.split(maxsplit=1)
        amount = float(parts[0])
        note = parts[1] if len(parts) > 1 else "အကြောင်းအရာမရှိ"
        
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO transactions (user_id, type, amount, note) VALUES (?, ?, ?, ?)",
                       (message.from_user.id, trans_type, amount, note))
        conn.commit()
        conn.close()
        
        type_str = "➕ ဝင်ငွေ" if trans_type == 'income' else "➖ ထွက်ငွေ"
        res = f"✅ စာရင်းမှတ်ပြီးပါပြီ!\n\nအမျိုးအစား: {type_str}\nပမာဏ: {amount:,.0f} ကျပ်\nအကြောင်းအရာ: {note}"
        bot.send_message(message.chat.id, res, reply_markup=main_menu())
    except Exception:
        bot.send_message(message.chat.id, "⚠️ မှားယွင်းနေပါသည်။ ပမာဏကို အရင်ရိုက်ပါ (ဥပမာ- 2000 မုန့်ဖိုး)။", reply_markup=main_menu())

# ----------------- အစီရင်ခံစာများ -----------------
@bot.message_handler(func=lambda m: m.text == "📅 ဒီနေ့စာရင်း")
@check_channel
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
        bot.send_message(message.chat.id, "📅 ဒီနေ့အတွက် မှတ်ထားသော စာရင်းများ မရှိသေးပါ။")
        return
        
    text = "📅 ဒီနေ့ စာရင်းချုပ်\n---------------------------\n"
    for row in rows:
        t_type, amount, note, time_str = row
        symbol = "🟢 +" if t_type == 'income' else "🔴 -"
        text += f"[{time_str}] {symbol} {amount:,.0f} ကျပ် ({note})\n"
        
    text += f"---------------------------\n🟢 ဒီနေ့ ဝင်ငွေ: {total_inc:,.0f} ကျပ်\n🔴 ဒီနေ့ ထွက်ငွေ: {total_exp:,.0f} ကျပ်\n⚖️ ဒီနေ့ လက်ကျန်: {(total_inc - total_exp):,.0f} ကျပ်"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🗓 ဒီလစာရင်း")
@check_channel
def show_month_report(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(CASE WHEN type='income' THEN amount ELSE 0 END), SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) FROM transactions WHERE user_id=? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now', 'localtime')", (user_id,))
    total_inc, total_exp = cursor.fetchone()
    cursor.execute("SELECT note, SUM(amount) FROM transactions WHERE user_id=? AND type='expense' AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now', 'localtime') GROUP BY note ORDER BY SUM(amount) DESC LIMIT 5", (user_id,))
    top_expenses = cursor.fetchall()
    conn.close()
    
    total_inc = total_inc or 0.0
    total_exp = total_exp or 0.0
    
    text = f"🗓 ဒီလ ဘဏ္ဍာရေး အစီရင်ခံစာ\n---------------------------\n🟢 ဝင်ငွေစုစုပေါင်း: {total_inc:,.0f} ကျပ်\n🔴 ထွက်ငွေစုစုပေါင်း: {total_exp:,.0f} ကျပ်\n💰 ဒီလ ပိုငွေ: {(total_inc - total_exp):,.0f} ကျပ်\n\n"
    if top_expenses:
        text += "🔥 ဒီလ အများဆုံး သုံးထားသည်များ:\n"
        for idx, (note, amt) in enumerate(top_expenses, 1):
            text += f"{idx}. {note}: {amt:,.0f} ကျပ်\n"
            
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "💰 စုစုပေါင်းလက်ကျန်")
@check_channel
def check_total_balance(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='income'", (user_id,))
    total_income = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE user_id=? AND type='expense'", (user_id,))
    total_expense = cursor.fetchone()[0] or 0.0
    conn.close()
    
    text = f"🏦 စုစုပေါင်း စာရင်းချုပ်\n\n🟢 ဝင်ငွေ: {total_income:,.0f} ကျပ်\n🔴 ထွက်ငွေ: {total_expense:,.0f} ကျပ်\n---------------------------\n💰 လက်ရှိကျန်ငွေ: {(total_income - total_expense):,.0f} ကျပ်"
    bot.send_message(message.chat.id, text)

# ----------------- Feature အသစ်များ (Excel / Backup / Delete) -----------------
@bot.message_handler(func=lambda m: m.text == "📥 Excel ထုတ်မည်")
@check_channel
def export_excel(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT date, type, amount, note FROM transactions WHERE user_id=? ORDER BY date DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "ထုတ်ယူရန် စာရင်းမရှိသေးပါ။")
        return

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Amount", "Note"])
    for r in rows:
        t_type = "Income" if r[1] == 'income' else "Expense"
        writer.writerow([r[0], t_type, r[2], r[3]])
    
    bio = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    bio.name = f'Transactions_{message.from_user.username or user_id}.csv'
    bot.send_document(message.chat.id, bio, caption="📊 စာရင်းမှတ်တမ်း Excel (.csv) ဖိုင် ရပါပြီ။")

@bot.message_handler(func=lambda m: m.text == "💾 Backup ယူမည်")
@check_channel
def backup_db(message):
    if os.path.exists('accounting.db'):
        with open('accounting.db', 'rb') as f:
            bot.send_document(message.chat.id, f, caption="💾 Database Backup ဖိုင် ရပါပြီ။\n(ဤဖိုင်ကို သိမ်းထားပါက စာရင်းများ ဘယ်တော့မှ မပျောက်တော့ပါ။)")
    else:
        bot.send_message(message.chat.id, "Database ဖိုင် မတွေ့ပါ။")

@bot.message_handler(func=lambda m: m.text == "❌ စာရင်းဖျက်မည်")
@check_channel
def delete_menu(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, amount, note, strftime('%Y-%m-%d', date) FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 5", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "ဖျက်စရာ စာရင်းမရှိသေးပါ။")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        t_id, t_type, amount, note, date = r
        symbol = "+" if t_type == 'income' else "-"
        btn_text = f"[{date}] {symbol}{amount:,.0f} ({note})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"del_{t_id}"))
    
    markup.add(types.InlineKeyboardButton("ပယ်ဖျက်မည်", callback_data="cancel_reset"))
    bot.send_message(message.chat.id, "ဖျက်လိုသော စာရင်းကို ရွေးချယ်ပါ (နောက်ဆုံးသွင်းထားသော ၅ ခု) -", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def process_delete(call):
    t_id = call.data.split("_")[1]
    conn = sqlite3.connect('accounting.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (t_id, call.from_user.id))
    conn.commit()
    conn.close()
    bot.edit_message_text("✅ ရွေးချယ်ထားသော စာရင်းကို ဖျက်လိုက်ပါပြီ။", call.message.chat.id, call.message.message_id)

# ----------------- စာရင်းအသစ်ပြန်စရန် -----------------
@bot.message_handler(func=lambda m: m.text == "🔄 စာရင်းအသစ်ပြန်စမည်")
@check_channel
def reset_confirm(message):
    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ ဟုတ်ကဲ့၊ အကုန်ဖျက်မည်", callback_data="confirm_reset")
    btn_no = types.InlineKeyboardButton("❌ မဖျက်တော့ပါ", callback_data="cancel_reset")
    markup.add(btn_yes, btn_no)
    bot.send_message(
        message.chat.id, 
        "⚠️ **သတိပေးချက်:**\nယခင် မှတ်ထားသော စာရင်းများအားလုံး ပျက်သွားမည်ဖြစ်သည်။ စာရင်းအသစ်မှ ပြန်စရန် သေချာပါသလား?", 
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_reset", "cancel_reset"])
def handle_reset_choice(call):
    if call.data == "confirm_reset":
        conn = sqlite3.connect('accounting.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE user_id=?", (call.from_user.id,))
        conn.commit()
        conn.close()
        bot.edit_message_text("✅ စာရင်းများအားလုံးကို အောင်မြင်စွာ ဖျက်လိုက်ပါပြီ။ စာရင်းအသစ် စတင် မှတ်နိုင်ပါပြီ။", call.message.chat.id, call.message.message_id)
    elif call.data == "cancel_reset":
        bot.edit_message_text("❌ လုပ်ဆောင်ချက်ကို ပယ်ဖျက်လိုက်ပါသည်။", call.message.chat.id, call.message.message_id)

print("Bot runs successfully! Waiting for messages...")
bot.infinity_polling()
        
