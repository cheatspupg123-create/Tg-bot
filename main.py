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

ACTIVE_GAMES_21 = {}

# --- БАЗА ДАННЫХ С ПОДДЕРЖКОЙ БУСТОВ И ТРАНЗАКЦИЙ ---
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
            boost_end_time INTEGER DEFAULT 0
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
        initial_items = ["🗡️ Меч самурая", "🏺 Древняя ваза", "⚡ Энергетик", "👑 Золотая корона", "🍕 Огромный кусок пиццы"]
        item = random.choice(initial_items)
        cursor.execute("INSERT INTO auction (id, item_name, current_price, highest_bidder, highest_bidder_name, end_time) VALUES (1, ?, ?, 0, ?, ?)",
                       (item, 1000.0, "Никто", end_time))
                       
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, properties, investments, accessories, equipped_accessory, last_bonus, quest_stage, quest_claimed, boost_end_time FROM users WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (chat_id, balance, properties, investments, accessories, equipped_accessory, last_bonus, quest_stage, quest_claimed, boost_end_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       (chat_id, 15.0, "", "", "", "", 0, 1, 0, 0))
        conn.commit()
        user_data = {
            "balance": 15.0, "properties": [], "investments": [], "accessories": [], 
            "equipped": "", "last_bonus": 0, "quest_stage": 1, "quest_claimed": 0, "boost_end_time": 0
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
            "boost_end_time": row[8]
        }
    conn.close()
    return user_data

def save_user(chat_id, user_data):
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("""
            UPDATE users SET balance = ?, properties = ?, investments = ?, accessories = ?, 
            equipped_accessory = ?, last_bonus = ?, quest_stage = ?, quest_claimed = ?, boost_end_time = ? 
            WHERE chat_id = ?
        """, (
            user_data["balance"], ",".join(user_data["properties"]), ",".join(user_data["investments"]), 
            ",".join(user_data["accessories"]), user_data["equipped"], user_data["last_bonus"], 
            user_data["quest_stage"], user_data["quest_claimed"], user_data["boost_end_time"], chat_id
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка сохранения данных пользователя {chat_id}: {e}")
    finally:
        conn.close()

HOUSES = {
    "house_1": {"name": "🏠 Шалаш", "price": 20, "income": 0.2},
    "house_2": {"name": "🛖 Хижина", "price": 50, "income": 0.6},
    "house_3": {"name": "🏚️ Лачуга", "price": 120, "income": 1.6},
    "house_4": {"name": "⛺ Палаточный лагерь", "price": 300, "income": 4.0},
    "house_5": {"name": "🏠 Гараж", "price": 700, "income": 10.0},
    "house_6": {"name": "🏢 Офис стартапа", "price": 1500, "income": 25.0},
    "house_7": {"name": "🏭 Завод", "price": 4000, "income": 70.0},
    "house_8": {"name": "💎 Небоскреб", "price": 10000, "income": 180.0}
}

INVESTMENTS = {
    "inv_0": {"name": "☕ Кофейный ларек", "price": 10, "income": 2.0},
    "inv_1": {"name": "🌱 Крипто-ферма", "price": 75, "income": 2.6},
    "inv_2": {"name": "🪙 Криптобиржа", "price": 500, "income": 15.0},
    "inv_3": {"name": "🚀 Космическая программа", "price": 5000, "income": 100.0}
}

CARDS = {
    '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'Валет (J)': 2, 'Дама (Q)': 3, 'Король (K)': 4, 'Туз (A)': 11
}

def calculate_score(cards):
    score = sum(CARDS[c] for c in cards)
    aces = cards.count('Туз (A)')
    while score > 21 and aces > 0:
        score -= 10
        aces -= 1
    return score

def main_menu_markup(user_data):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("👤 Профиль", callback_data="profile_menu"), InlineKeyboardButton("💰 Баланс", callback_data="balance"))
    markup.row(InlineKeyboardButton("🏢 Бизнесы", callback_data="shop"), InlineKeyboardButton("📈 Инвестиции", callback_data="invest_menu"))
    markup.row(InlineKeyboardButton("🎲 Сыграть в 21", callback_data="start_21"), InlineKeyboardButton("⚔️ Дуэль", callback_data="duel_menu"))
    markup.row(InlineKeyboardButton("🎒 Инвентарь", callback_data="inventory_menu"), InlineKeyboardButton("📂 Имущество", callback_data="my_props"))
    markup.row(InlineKeyboardButton("⭐ Донат-магазин", callback_data="donate_shop"), InlineKeyboardButton("🏛️ Аукцион", callback_data="auction_menu"))
    markup.row(InlineKeyboardButton("🎁 Бонус", callback_data="get_test_item"))
    return markup

@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_data = get_user(message.chat.id)
    bot.send_message(message.chat.id, "🌆 Добро пожаловать! Расширенный донат-магазин активен.", reply_markup=main_menu_markup(user_data))

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
            save_user(target_id, user)
            bot.send_message(message.chat.id, f"✅ Выдано {amount} монет игроку `{target_id}`.", parse_mode="Markdown")
        elif len(parts) == 2:
            amount = float(parts[1])
            user = get_user(message.chat.id)
            user["balance"] += amount
            save_user(message.chat.id, user)
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
        
        boost_status = "❌ Отключен"
        if user_data['boost_end_time'] > time.time():
            left_mins = int((user_data['boost_end_time'] - time.time()) / 60)
            boost_status = f"⚡ Активен (ещё {left_mins} мин.)"

        text = (
            f"👤 **Профиль**\n\n"
            f"🆔 ID: `{chat_id}`\n"
            f"💰 Баланс: **{round(user_data['balance'], 2)} монет**\n"
            f"🚀 Буст прибыли x3: {boost_status}\n"
            f"Надето: {equipped_str}"
        )
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=main_menu_markup(user_data), parse_mode="Markdown")

    elif call.data == "balance":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"💰 Баланс: {round(user_data['balance'], 2)} монет", reply_markup=main_menu_markup(user_data))

    elif call.data == "shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in HOUSES.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет", callback_data=f"buy_coin_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🏪 Магазин бизнесов:", reply_markup=markup)

    elif call.data == "invest_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in INVESTMENTS.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет", callback_data=f"buy_inv_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="📈 Инвестиции:", reply_markup=markup)

    elif call.data.startswith("buy_inv_") or call.data.startswith("buy_coin_"):
        is_inv = call.data.startswith("buy_inv_")
        key = call.data.replace("buy_inv_" if is_inv else "buy_coin_", "")
        item = INVESTMENTS.get(key) if is_inv else HOUSES.get(key)
        if item and user_data["balance"] >= item["price"]:
            user_data["balance"] -= item["price"]
            (user_data["investments"] if is_inv else user_data["properties"]).append(item["name"])
            save_user(chat_id, user_data)
            bot.answer_callback_query(call.id, "Успешно куплено!", show_alert=True)
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="✅ Покупка завершена!", reply_markup=main_menu_markup(user_data))
        else:
            bot.answer_callback_query(call.id, "Недостаточно средств!", show_alert=True)

    # --- РАСШИРЕННЫЙ ДОНАТ-МАГАЗИН (TELEGRAM STARS) ---
    elif call.data == "donate_shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("⭐ 100 монет (10 звёзд)", callback_data="donate_coins_100"))
        markup.row(InlineKeyboardButton("⭐ 500 монет (50 звёзд)", callback_data="donate_coins_500"))
        markup.row(InlineKeyboardButton("🚀 Буст прибыли x3 на 3 часа (75 звёзд)", callback_data="donate_boost_3h"))
        markup.row(InlineKeyboardButton("👑 Корона Императора (Аксессуар) [150 звёзд]", callback_data="donate_item_crown"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        text = (
            "⭐ **Премиум-магазин (Telegram Stars)**\n\n"
            "Ускорьте свой прогресс с помощью уникальных донат-услуг:"
        )
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("donate_coins_"):
        coins = int(call.data.replace("donate_coins_", ""))
        price_stars = int(coins / 10)
        bot.answer_callback_query(call.id)
        bot.send_invoice(
            chat_id=chat_id, title=f"Покупка {coins} монет",
            description="Игровая валюта", invoice_payload=f"buy_coins_{coins}",
            provider_token="", currency="XTR", prices=[LabeledPrice(label=f"{coins} монет", amount=price_stars)]
        )

    elif call.data == "donate_boost_3h":
        bot.answer_callback_query(call.id)
        bot.send_invoice(
            chat_id=chat_id, title="Буст прибыли x3 (3 часа)",
            description="Увеличение дохода от всех бизнесов в 3 раза на 3 часа", invoice_payload="buy_boost_x3",
            provider_token="", currency="XTR", prices=[LabeledPrice(label="Буст x3", amount=75)]
        )

    elif call.data == "donate_item_crown":
        bot.answer_callback_query(call.id)
        bot.send_invoice(
            chat_id=chat_id, title="Эксклюзивный аксессуар: 👑 Корона Императора",
            description="Уникальный предмет роскоши в инвентарь", invoice_payload="buy_item_crown",
            provider_token="", currency="XTR", prices=[LabeledPrice(label="Корона Императора", amount=150)]
        )

    elif call.data == "get_test_item":
        test_items = ["⚔️ Стальной меч", "🛡️ Железный щит", "⚡ Энергетик", "🕶️ Очки"]
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
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=main_menu_markup(user_data))

    elif call.data == "start_21":
        bot.answer_callback_query(call.id)
        if user_data["balance"] < 5:
            bot.answer_callback_query(call.id, "❌ Минимальная ставка 5 монет!", show_alert=True)
            return
        
        bet = 5.0
        deck = list(CARDS.keys()) * 4
        random.shuffle(deck)
        player_cards = [deck.pop(), deck.pop()]
        dealer_cards = [deck.pop(), deck.pop()]
        
        ACTIVE_GAMES_21[chat_id] = {"deck": deck, "player_cards": player_cards, "dealer_cards": dealer_cards, "bet": bet}
        p_score = calculate_score(player_cards)
        
        text = f"🃏 **Игра в 21**\n\nВаши карты: {', '.join(player_cards)} (Очки: **{p_score}**)\nКарта дилера: {dealer_cards[0]}, [скрыто]"
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("➕ Взять", callback_data="game21_hit"), InlineKeyboardButton("🛑 Хватит", callback_data="game21_stand"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "game21_hit":
        bot.answer_callback_query(call.id)
        if chat_id not in ACTIVE_GAMES_21:
            return
        game = ACTIVE_GAMES_21[chat_id]
        game["player_cards"].append(game["deck"].pop())
        p_score = calculate_score(game["player_cards"])
        
        if p_score > 21:
            user_data["balance"] -= game["bet"]
            save_user(chat_id, user_data)
            text = f"💥 **Перебор! Проигрыш.**\nКарты: {', '.join(game['player_cards'])} ({p_score})\nБаланс: {round(user_data['balance'], 2)}"
            del ACTIVE_GAMES_21[chat_id]
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=main_menu_markup(user_data), parse_mode="Markdown")
        else:
            text = f"🃏 **Игра в 21**\nКарты: {', '.join(game['player_cards'])} (Очки: **{p_score}**)"
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("➕ Взять", callback_data="game21_hit"), InlineKeyboardButton("🛑 Хватит", callback_data="game21_stand"))
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "game21_stand":
        bot.answer_callback_query(call.id)
        if chat_id not in ACTIVE_GAMES_21:
            return
        game = ACTIVE_GAMES_21[chat_id]
        p_score = calculate_score(game["player_cards"])
        d_score = calculate_score(game["dealer_cards"])
        
        while d_score < 17 and len(game["deck"]) > 0:
            game["dealer_cards"].append(game["deck"].pop())
            d_score = calculate_score(game["dealer_cards"])
            
        bet = game["bet"]
        if d_score > 21 or p_score > d_score:
            user_data["balance"] += bet
            res = f"🎉 **Победа!** +{bet} монет"
        elif p_score == d_score:
            res = "🤝 **Ничья!**"
        else:
            user_data["balance"] -= bet
            res = f"😢 **Поражение!** -{bet} монет"
            
        save_user(chat_id, user_data)
        text = f"{res}\nВаши: {p_score} | Дилер: {d_score}\nБаланс: {round(user_data['balance'], 2)}"
        del ACTIVE_GAMES_21[chat_id]
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=main_menu_markup(user_data), parse_mode="Markdown")

    elif call.data == "duel_menu":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="⚔️ Раздел дуэлей в разработке.", reply_markup=main_menu_markup(user_data))

    elif call.data == "auction_menu":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🏛️ Аукцион активен.", reply_markup=main_menu_markup(user_data))

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    user = get_user(message.chat.id)
    
    if payload.startswith("buy_coins_"):
        coins = float(payload.replace("buy_coins_", ""))
        user["balance"] += coins
        save_user(message.chat.id, user)
        bot.send_message(message.chat.id, f"✅ Оплата успешна! Зачислено **{coins} монет**.", parse_mode="Markdown")
        
    elif payload == "buy_boost_x3":
        current_time = int(time.time())
        base_time = max(current_time, user["boost_end_time"])
        user["boost_end_time"] = base_time + (3 * 3600)  # +3 часа
        save_user(message.chat.id, user)
        bot.send_message(message.chat.id, "🚀 **Буст прибыли x3 успешно активирован на 3 часа!**", parse_mode="Markdown")
        
    elif payload == "buy_item_crown":
        item = "👑 Корона Императора"
        if item not in user["accessories"]:
            user["accessories"].append(item)
        save_user(message.chat.id, user)
        bot.send_message(message.chat.id, f"👑 Покупка завершена! В ваш инвентарь добавлен предмет: **{item}**.", parse_mode="Markdown")

if __name__ == "__main__":
    init_db()
    logging.info("Бот запущен с расширенным донатом и транзакциями БД.")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            logging.error(f"Ошибка polling: {e}")
            time.sleep(5)
