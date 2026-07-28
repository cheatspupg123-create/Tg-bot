import time
import logging
import sqlite3
import random
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice

TOKEN = "8631846961:AAGpjWYBTBugvefFkiWBSucihBEZBthlY2M"
ADMIN_ID = 5107814486

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 15.0,
            properties TEXT DEFAULT "",
            investments TEXT DEFAULT "",
            accessories TEXT DEFAULT "",
            equipped_accessory TEXT DEFAULT "",
            last_bonus INTEGER DEFAULT 0,
            quest_stage INTEGER DEFAULT 1,
            quest_claimed INTEGER DEFAULT 0,
            total_earned REAL DEFAULT 0.0,
            total_spent REAL DEFAULT 0.0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            amount REAL,
            type TEXT,
            timestamp INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            seller_name TEXT,
            item_name TEXT,
            price REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auction (
            id INTEGER PRIMARY KEY,
            item_name TEXT,
            current_price REAL,
            highest_bidder INTEGER,
            highest_bidder_name TEXT,
            end_time INTEGER
        )
    ''')
    
    cursor.execute("SELECT id FROM auction WHERE id = 1")
    if not cursor.fetchone():
        end_time = int(time.time()) + 21600
        initial_items = ["🗡️ Меч самурая", "🏺 Древняя ваза", "⚡ Энергетик", "👑 Золотая корона", "🍕 Пицца"]
        item = random.choice(initial_items)
        cursor.execute("INSERT INTO auction (id, item_name, current_price, highest_bidder, highest_bidder_name, end_time) VALUES (1, ?, ?, 0, ?, ?)",
                       (item, 1000.0, "Никто", end_time))
                       
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, properties, investments, accessories, equipped_accessory, last_bonus, quest_stage, quest_claimed, total_earned, total_spent FROM users WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (chat_id, balance, properties, investments, accessories, equipped_accessory, last_bonus, quest_stage, quest_claimed, total_earned, total_spent) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       (chat_id, 15.0, "", "", "", "", 0, 1, 0, 0.0, 0.0))
        conn.commit()
        user_data = {
            "balance": 15.0, "properties": [], "investments": [], "accessories": [], 
            "equipped": "", "last_bonus": 0, "quest_stage": 1, "quest_claimed": 0,
            "total_earned": 0.0, "total_spent": 0.0
        }
    else:
        user_data = {
            "balance": row[0],
            "properties": row[1].split(",") if row[1] else [],
            "investments": row[2].split(",") if row[2] else [],
            "accessories": row[3].split(",") if row[3] else [],
            "equipped": row[4] if row[4] else "",
            "last_bonus": row[5],
            "quest_stage": row[6],
            "quest_claimed": row[7],
            "total_earned": row[8],
            "total_spent": row[9]
        }
    conn.close()
    return user_data

def save_user(chat_id, user_data, tx_amount=0.0, tx_type=""):
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("""
            UPDATE users SET balance = ?, properties = ?, investments = ?, accessories = ?, 
            equipped_accessory = ?, last_bonus = ?, quest_stage = ?, quest_claimed = ?, 
            total_earned = ?, total_spent = ? WHERE chat_id = ?
        """, (
            user_data["balance"], ",".join(user_data["properties"]), ",".join(user_data["investments"]), 
            ",".join(user_data["accessories"]), user_data["equipped"], user_data["last_bonus"], 
            user_data["quest_stage"], user_data["quest_claimed"], user_data["total_earned"], 
            user_data["total_spent"], chat_id
        ))
        
        if tx_amount != 0 and tx_type:
            cursor.execute("INSERT INTO transactions (chat_id, amount, type, timestamp) VALUES (?, ?, ?, ?)",
                           (chat_id, tx_amount, tx_type, int(time.time())))
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка сохранения пользователя {chat_id}: {e}")
    finally:
        conn.close()

def get_user_transactions(chat_id, limit=7):
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT amount, type, timestamp FROM transactions WHERE chat_id = ? ORDER BY id DESC LIMIT ?", (chat_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

HOUSES = {
    "house_1": {"name": "🏠 Шалаш", "price": 30, "income": 0.1},
    "house_2": {"name": "🛖 Хижина", "price": 90, "income": 0.3},
    "house_3": {"name": "🏚️ Лачуга", "price": 250, "income": 0.8},
    "house_4": {"name": "⛺ Палаточный лагерь", "price": 650, "income": 2.0},
    "house_5": {"name": "🏠 Гаражная мастерская", "price": 1500, "income": 4.5},
    "house_6": {"name": "🏢 Офис стартапа", "price": 3500, "income": 10.0},
    "house_7": {"name": "🍔 Закусочная", "price": 8000, "income": 22.0},
    "house_8": {"name": "⛽ Автомойка", "price": 18000, "income": 48.0},
    "house_9": {"name": "🏨 Мини-отель", "price": 40000, "income": 105.0},
    "house_10": {"name": "🏭 Завод", "price": 90000, "income": 230.0},
    "house_11": {"name": "🛒 Супермаркет", "price": 200000, "income": 500.0},
    "house_12": {"name": "💎 Небоскреб", "price": 450000, "income": 1100.0},
    "house_13": {"name": "🚢 Морской порт", "price": 1000000, "income": 2400.0},
    "house_14": {"name": "🛫 Авиакомпания", "price": 2200000, "income": 5200.0},
    "house_15": {"name": "🛢️ Нефтяная вышка", "price": 5000000, "income": 11500.0},
    "house_16": {"name": "⚡ АЭС", "price": 11000000, "income": 25000.0},
    "house_17": {"name": "🔬 Научный комплекс", "price": 25000000, "income": 55000.0},
    "house_18": {"name": "🪐 Космическая станция", "price": 55000000, "income": 120000.0},
    "house_19": {"name": "🌐 Мегаполис", "price": 120000000, "income": 260000.0},
    "house_20": {"name": "🌌 Межгалактический холдинг", "price": 270000000, "income": 580000.0}
}

INVESTMENTS = {
    "inv_1": {"name": "☕ Кофейный ларек", "price": 20, "income": 0.15},
    "inv_2": {"name": "📰 Газетный киоск", "price": 60, "income": 0.45},
    "inv_3": {"name": "🌱 Крипто-ферма", "price": 180, "income": 1.2},
    "inv_4": {"name": "🪙 Криптобиржа", "price": 450, "income": 3.0},
    "inv_5": {"name": "🎨 NFT-студия", "price": 1100, "income": 7.5},
    "inv_6": {"name": "🤖 ИИ-разработка", "price": 2800, "income": 18.0},
    "inv_7": {"name": "🔋 Производство батарей", "price": 6500, "income": 42.0},
    "inv_8": {"name": "🛰️ Спутниковая связь", "price": 15000, "income": 95.0},
    "inv_9": {"name": "🧬 Био-лаборатория", "price": 35000, "income": 220.0},
    "inv_10": {"name": "⚡ Термоядерный реактор", "price": 80000, "income": 490.0},
    "inv_11": {"name": "🌌 Телескоп глубокого космоса", "price": 180000, "income": 1100.0},
    "inv_12": {"name": "🚀 Частная космонавтика", "price": 400000, "income": 2400.0},
    "inv_13": {"name": "🦾 Кибернетические протезы", "price": 900000, "income": 5300.0},
    "inv_14": {"name": "🧠 Нейроинтерфейсы", "price": 2000000, "income": 11800.0},
    "inv_15": {"name": "🌊 Терраформирование океанов", "price": 4500000, "income": 26500.0},
    "inv_16": {"name": "🌍 Озеленение Марса", "price": 10000000, "income": 60000.0},
    "inv_17": {"name": "⏳ Машина времени (прототип)", "price": 23000000, "income": 135000.0},
    "inv_18": {"name": "🌀 Генератор искривления", "price": 50000000, "income": 300000.0},
    "inv_19": {"name": "🔮 Квантовый суперкомпьютер", "price": 110000000, "income": 670000.0},
    "inv_20": {"name": "✨ Сингулярный фонд", "price": 250000000, "income": 1500000.0}
}

def main_menu_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("👤 Профиль", callback_data="profile_menu"), InlineKeyboardButton("💰 Баланс", callback_data="balance"))
    markup.row(InlineKeyboardButton("🏢 Бизнесы", callback_data="shop"), InlineKeyboardButton("📈 Инвестиции", callback_data="invest_menu"))
    markup.row(InlineKeyboardButton("🎒 Инвентарь", callback_data="inventory_menu"), InlineKeyboardButton("📂 Имущество", callback_data="my_props"))
    markup.row(InlineKeyboardButton("⭐ Донат-магазин", callback_data="donate_shop"), InlineKeyboardButton("📜 История доходов", callback_data="history_menu"))
    markup.row(InlineKeyboardButton("🏛️ Аукцион", callback_data="auction_menu"), InlineKeyboardButton("🛒 Рынoк", callback_data="market_menu"))
    markup.row(InlineKeyboardButton("🎁 Бонус", callback_data="get_test_item"))
    return markup

@bot.message_handler(commands=["start"])
def send_welcome(message):
    get_user(message.chat.id)
    bot.send_message(message.chat.id, "🌆 Добро пожаловать! Экономика ужесточена, добавлено по 20 бизнесов и инвестиций.", reply_markup=main_menu_markup())

@bot.message_handler(commands=["addmoney"])
def cmd_add_money(message):
    if message.chat.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        if len(parts) >= 3:
            target_id = int(parts[1])
            amount = float(parts[2])
            user = get_user(target_id)
            user["balance"] += amount
            user["total_earned"] += amount
            save_user(target_id, user, amount, "Админ бонус")
            bot.send_message(message.chat.id, f"✅ Выдано {amount} монет игроку `{target_id}`.", parse_mode="Markdown")
        elif len(parts) == 2:
            amount = float(parts[1])
            user = get_user(message.chat.id)
            user["balance"] += amount
            user["total_earned"] += amount
            save_user(message.chat.id, user, amount, "Админ бонус")
            bot.send_message(message.chat.id, f"✅ Выдано себе: {amount} монет.")
    except Exception:
        bot.send_message(message.chat.id, "❌ Ошибка в команде.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user_data = get_user(chat_id)

    if call.data == "profile_menu" or call.data == "menu":
        bot.answer_callback_query(call.id)
        equipped_str = f"✨ {user_data['equipped']}" if user_data['equipped'] else "✨ Ничего"
        text = (
            f"👤 **Профиль (Строгая экономика)**\n\n"
            f"🆔 ID: `{chat_id}`\n"
            f"💰 Баланс: **{round(user_data['balance'], 2)} монет**\n"
            f"📈 Всего заработано: **{round(user_data['total_earned'], 2)} монет**\n"
            f"📉 Всего потрачено: **{round(user_data['total_spent'], 2)} монет**\n"
            f"✨ Надето: {equipped_str}"
        )
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=main_menu_markup(), parse_mode="Markdown")

    elif call.data == "balance":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"💰 Баланс: {round(user_data['balance'], 2)} монет", reply_markup=main_menu_markup())

    elif call.data == "shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in HOUSES.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет", callback_data=f"buy_coin_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🏪 Магазин бизнесов (20 уровней):", reply_markup=markup)

    elif call.data == "invest_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in INVESTMENTS.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет", callback_data=f"buy_inv_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="📈 Инвестиции (20 вариантов):", reply_markup=markup)

    elif call.data.startswith("buy_inv_") or call.data.startswith("buy_coin_"):
        is_inv = call.data.startswith("buy_inv_")
        key = call.data.replace("buy_inv_" if is_inv else "buy_coin_", "")
        item = INVESTMENTS.get(key) if is_inv else HOUSES.get(key)
        if item and user_data["balance"] >= item["price"]:
            user_data["balance"] -= item["price"]
            user_data["total_spent"] += item["price"]
            (user_data["investments"] if is_inv else user_data["properties"]).append(item["name"])
            save_user(chat_id, user_data, -item["price"], f"Покупка: {item['name']}")
            bot.answer_callback_query(call.id, "Успешно куплено!", show_alert=True)
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="✅ Покупка завершена!", reply_markup=main_menu_markup())
        else:
            bot.answer_callback_query(call.id, "Недостаточно средств!", show_alert=True)

    elif call.data == "donate_shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("⭐ 10 000 монет (10 звёзд)", callback_data="donate_10000"))
        markup.row(InlineKeyboardButton("⭐ 50 000 монет (50 звёзд)", callback_data="donate_50000"))
        markup.row(InlineKeyboardButton("⭐ 150 000 монет (100 звёзд)", callback_data="donate_150000"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        text = "⭐ **Донат-магазин (Telegram Stars)**\n\nВыберите пакет монет для мгновенного пополнения:"
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("donate_"):
        coins = int(call.data.replace("donate_", ""))
        if coins == 10000:
            price_stars = 10
        elif coins == 50000:
            price_stars = 50
        elif coins == 150000:
            price_stars = 100
        else:
            price_stars = int(coins / 1000)
            
        bot.answer_callback_query(call.id)
        bot.send_invoice(
            chat_id=chat_id, title=f"Покупка {coins} монет",
            description="Игровая валюта за Telegram Stars", invoice_payload=f"buy_coins_{coins}",
            provider_token="", currency="XTR", prices=[LabeledPrice(label=f"{coins} монет", amount=price_stars)]
        )

    elif call.data == "history_menu":
        bot.answer_callback_query(call.id)
        txs = get_user_transactions(chat_id, limit=7)
        text = "📜 **История доходов и транзакций:**\n\n"
        if txs:
            for amount, t_type, ts in txs:
                sign = "+" if amount > 0 else ""
                date_str = time.strftime('%d.%m %H:%M', time.localtime(ts))
                text += f"• `{date_str}` | {t_type}: **{sign}{round(amount, 2)}**\n"
        else:
            text += "История пока пуста."
            
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "auction_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🏛️ **Аукцион уникальных предметов**\n\nРаздел активен, торги идут.", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "market_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🛒 **P2P Рынок**\n\nЗдесь игроки могут торговать предметами.", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "get_test_item":
        test_items = ["👑 Золотая корона", "🗡️ Меч самурая", "⚡ Энергетик", "🕶️ Очки"]
        item = random.choice(test_items)
        if item not in user_data["accessories"]:
            user_data["accessories"].append(item)
            save_user(chat_id, user_data)
            bot.answer_callback_query(call.id, f"🎁 Получен предмет: {item}!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Этот предмет уже у вас есть!", show_alert=True)
        callback_handler(call)

    elif call.data == "inventory_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        equipped_text = f"✨ Надето: **{user_data['equipped']}**" if user_data['equipped'] else "✨ Надето: **Ничего**"
        
        if user_data["accessories"]:
            text = f"🎒 **Инвентарь**\n\n{equipped_text}\n\nНажмите, чтобы надеть/снять:"
            for idx, acc in enumerate(user_data["accessories"]):
                prefix = "🟢 [Надето] " if acc == user_data["equipped"] else ""
                markup.row(InlineKeyboardButton(f"{prefix}{acc}", callback_data=f"equip_acc_{idx}"))
        else:
            text = f"🎒 **Инвентарь пуст**\n\n{equipped_text}"
            
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("equip_acc_"):
        try:
            idx = int(call.data.replace("equip_acc_", ""))
            if idx < len(user_data["accessories"]):
                item_name = user_data["accessories"][idx]
                if user_data["equipped"] == item_name:
                    user_data["equipped"] = ""
                else:
                    user_data["equipped"] = item_name
                save_user(chat_id, user_data)
                call.data = "inventory_menu"
                callback_handler(call)
        except Exception:
            bot.answer_callback_query(call.id, "Ошибка выбора предмета", show_alert=True)

    elif call.data == "my_props":
        bot.answer_callback_query(call.id)
        text = f"📂 Имущество:\nБизнесы: {', '.join(user_data['properties']) or 'нет'}\nИнвестиции: {', '.join(user_data['investments']) or 'нет'}"
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=main_menu_markup())

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    if payload.startswith("buy_coins_"):
        coins = float(payload.replace("buy_coins_", ""))
        user = get_user(message.chat.id)
        user["balance"] += coins
        user["total_earned"] += coins
        save_user(message.chat.id, user, coins, "Донат (Telegram Stars)")
        bot.send_message(message.chat.id, f"✅ Оплата прошла успешно! Вам начислено **{coins} монет**.", parse_mode="Markdown")

if __name__ == "__main__":
    init_db()
    logging.info("Бот со строгой экономикой (по 20 бизнесов и инвестиций) запущен.")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            logging.error(f"Ошибка polling: {e}")
            time.sleep(5)
