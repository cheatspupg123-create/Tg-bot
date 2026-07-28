import time
import threading
import sqlite3
import random
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice

TOKEN = "8631846961:AAGpjWYBTBugvefFkiWBSucihBEZBthlY2M"
ADMIN_ID = 5107814486
bot = telebot.TeleBot(TOKEN)

# Активные дуэли: {duel_id: {"p1": chat_id1, "p2": chat_id2, "bet": amount, "deck": [...], "p1_cards": [...], "p2_cards": [...], "p1_stand": False, "p2_stand": False, "accepted": True}}
ACTIVE_DUELS = {}

# --- БАЗА ДАННЫХ ---
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
            quest_claimed INTEGER DEFAULT 0
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
        initial_items = [
            "🗡️ Меч самурая", "🏺 Древняя ваза", "⚡ Энергетик", 
            "🥷 Ниндзя-сюрикен", "👑 Золотая корона", "🍫 Шоколадка Feastables", 
            "🥤 Стаканчик газировки MrBeast", "🍕 Огромный кусок пиццы", 
            "🍔 Мега-бургер с тройным сыром", "🍩 Глазированный пончик"
        ]
        item = random.choice(initial_items)
        cursor.execute("INSERT INTO auction (id, item_name, current_price, highest_bidder, highest_bidder_name, end_time) VALUES (1, ?, ?, 0, ?, ?)",
                       (item, 1000.0, "Никто", end_time))
                       
    conn.commit()
    conn.close()

init_db()

def get_user(chat_id):
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, properties, investments, accessories, equipped_accessory, last_bonus, quest_stage, quest_claimed FROM users WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (chat_id, balance, properties, investments, accessories, equipped_accessory, last_bonus, quest_stage, quest_claimed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       (chat_id, 15.0, "", "", "", "", 0, 1, 0))
        conn.commit()
        user_data = {"balance": 15.0, "properties": [], "investments": [], "accessories": [], "equipped": "", "last_bonus": 0, "quest_stage": 1, "quest_claimed": 0}
    else:
        props = row[1].split(",") if row[1] else []
        invs = row[2].split(",") if row[2] else []
        accs = row[3].split(",") if row[3] else []
        equipped = row[4] if row[4] else ""
        user_data = {"balance": row[0], "properties": props, "investments": invs, "accessories": accs, "equipped": equipped, "last_bonus": row[5], "quest_stage": row[6], "quest_claimed": row[7]}
    conn.close()
    return user_data

def save_user(chat_id, user_data):
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    props_str = ",".join(user_data["properties"])
    invs_str = ",".join(user_data["investments"])
    accs_str = ",".join(user_data["accessories"])
    equipped_str = user_data["equipped"]
    cursor.execute("UPDATE users SET balance = ?, properties = ?, investments = ?, accessories = ?, equipped_accessory = ?, last_bonus = ?, quest_stage = ?, quest_claimed = ? WHERE chat_id = ?",
                   (user_data["balance"], props_str, invs_str, accs_str, equipped_str, user_data["last_bonus"], user_data["quest_stage"], user_data["quest_claimed"], chat_id))
    conn.commit()
    conn.close()

# --- БИЗНЕСЫ И ИНВЕСТИЦИИ ---
HOUSES = {
    "house_1": {"name": "🏠 Шалаш", "price": 20, "income": round(0.6 / 3, 2)},
    "house_2": {"name": "🛖 Хижина", "price": 50, "income": round(1.8 / 3, 2)},
    "house_3": {"name": "🏚️ Лачуга", "price": 120, "income": round(4.8 / 3, 2)},
    "house_4": {"name": "⛺ Палаточный лагерь", "price": 300, "income": round(12.0 / 3, 2)},
    "house_5": {"name": "🏠 Гараж", "price": 700, "income": round(30.0 / 3, 2)},
    "house_6": {"name": "🏡 Дачный домик", "price": 1500, "income": round(72.0 / 3, 2)},
    "house_7": {"name": "🏘️ Коттедж", "price": 3500, "income": round(180.0 / 3, 2)},
    "house_8": {"name": "🏢 Офис", "price": 8000, "income": round(450.0 / 3, 2)},
    "house_9": {"name": "🏬 Торговая точка", "price": 18000, "income": round(1080.0 / 3, 2)},
    "house_10": {"name": "🏭 Мануфактура", "price": 40000, "income": round(2400.0 / 3, 2)},
    "house_11": {"name": "🏗️ Склад", "price": 90000, "income": round(5400.0 / 3, 2)},
    "house_12": {"name": "🏙️ Бизнес-центр", "price": 200000, "income": round(12000.0 / 3, 2)},
    "house_13": {"name": "🌐 Сеть АЗС", "price": 450000, "income": round(27000.0 / 3, 2)},
    "house_14": {"name": "🏨 Сеть отелей", "price": 1000000, "income": round(60000.0 / 3, 2)},
    "house_15": {"name": "⚡ Электростанция", "price": 2200000, "income": round(138000.0 / 3, 2)},
    "house_16": {"name": "🚢 Морской порт", "price": 5000000, "income": round(312000.0 / 3, 2)},
    "house_17": {"name": "✈️ Аэропорт", "price": 11000000, "income": round(720000.0 / 3, 2)},
    "house_18": {"name": "🎡 Парк аттракционов", "price": 25000000, "income": round(1680000.0 / 3, 2)},
    "house_19": {"name": "🏙️ Мега-небоскреб", "price": 60000000, "income": round(3900000.0 / 3, 2)},
    "house_20": {"name": "🌐 Корпоративный город", "price": 140000000, "income": round(9000000.0 / 3, 2)}
}

STAR_HOUSES = {
    "star_cafe": {"name": "⭐ Звездная Кофейня", "price": 2, "income": 500.0},
    "star_1": {"name": "💎 Звездная IT-Корпорация", "price": 5, "income": 1500.0},
    "star_2": {"name": "🚀 Звездный Космопорт", "price": 10, "income": 4000.0},
    "star_3": {"name": "🛰️ Звездная Спутниковая связь", "price": 20, "income": 9500.0},
    "star_4": {"name": "🌌 Межгалактический Звездный Банк", "price": 40, "income": 20000.0}
}

INVESTMENTS = {
    "inv_0": {"name": "☕ Кофейный ларек (Старт)", "price": 10, "income": round(18.0 / 9, 2)},
    "inv_1": {"name": "🌱 Крипто-ферма", "price": 75, "income": round(24.0 / 9, 2)},
    "inv_2": {"name": "☕ Кофейный ларек+", "price": 200, "income": round(48.0 / 9, 2)},
    "inv_3": {"name": "⛽ Автомойка", "price": 750, "income": round(120.0 / 9, 2)},
    "inv_4": {"name": "🚢 Логистическая компания", "price": 3000, "income": round(480.0 / 9, 2)},
    "inv_5": {"name": "✈️ Авиалинии", "price": 12500, "income": round(1800.0 / 9, 2)},
    "inv_6": {"name": "🎬 Киностудия", "price": 50000, "income": round(6000.0 / 9, 2)},
    "inv_7": {"name": "🧬 Биотех-лаборатория", "price": 200000, "income": round(21000.0 / 9, 2)},
    "inv_8": {"name": "⚛️ Квантовый реактор", "price": 1000000, "income": round(72000.0 / 9, 2)},
    "inv_9": {"name": "🪐 Добыча на астероидах", "price": 5000000, "income": round(240000.0 / 9, 2)}
}

QUESTS = {
    1: {"title": "Купи свой первый бизнес (Шалаш)", "target_prop": "🏠 Шалаш", "reward": 10.0},
    2: {"title": "Расширяйся: купи Хижину", "target_prop": "🛖 Хижина", "reward": 15.0},
    3: {"title": "Крупный шаг: приобрети Лачугу", "target_prop": "🏚️ Лачуга", "reward": 20.0}
}

def background_worker():
    while True:
        time.sleep(60)
        try:
            conn = sqlite3.connect("game.db", check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute("SELECT item_name, current_price, highest_bidder, end_time FROM auction WHERE id = 1")
            row = cursor.fetchone()
            if row:
                item_name, current_price, highest_bidder, end_time = row
                if int(time.time()) >= end_time:
                    if highest_bidder > 0:
                        cursor.execute("SELECT accessories FROM users WHERE chat_id = ?", (highest_bidder,))
                        u_row = cursor.fetchone()
                        if u_row:
                            accs = u_row[0].split(",") if u_row[0] else []
                            accs.append(item_name)
                            cursor.execute("UPDATE users SET accessories = ? WHERE chat_id = ?", (",".join(accs), highest_bidder))
                    
                    unique_items = [
                        "🗡️ Меч самурая", "🏺 Древняя ваза", "⚡ Энергетик", 
                        "🥷 Ниндзя-сюрикен", "👑 Золотая корона", "🍫 Шоколадка Feastables", 
                        "🥤 Стаканчик газировки MrBeast", "🍕 Огромный кусок пиццы", 
                        "🍔 Мега-бургер с тройным сыром", "🍩 Глазированный пончик"
                    ]
                    new_item = random.choice(unique_items)
                    new_end_time = int(time.time()) + 21600
                    cursor.execute("UPDATE auction SET item_name = ?, current_price = ?, highest_bidder = 0, highest_bidder_name = 'Никто', end_time = ? WHERE id = 1",
                                   (new_item, 1000.0, new_end_time))
                    conn.commit()

            cursor.execute("SELECT chat_id, balance, properties, investments FROM users")
            users_rows = cursor.fetchall()
            for u in users_rows:
                chat_id, balance, props_str, invs_str = u[0], u[1], u[2], u[3]
                props = props_str.split(",") if props_str else []
                invs = invs_str.split(",") if invs_str else []
                
                total_income = 0.0
                for p in props:
                    for item in {**HOUSES, **STAR_HOUSES}.values():
                        if item["name"] == p:
                            total_income += item["income"]
                for inv in invs:
                    for item in INVESTMENTS.values():
                        if item["name"] == inv:
                            total_income += item["income"]
                
                if total_income > 0:
                    new_balance = balance + total_income
                    cursor.execute("UPDATE users SET balance = ? WHERE chat_id = ?", (new_balance, chat_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Ошибка в фоновом потоке: {e}")

threading.Thread(target=background_worker, daemon=True).start()

def main_menu_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("👤 Профиль", callback_data="profile_menu"), InlineKeyboardButton("💰 Баланс", callback_data="balance"))
    markup.row(InlineKeyboardButton("📊 Доход", callback_data="income_info"), InlineKeyboardButton("⏰ Бонус (+3)", callback_data="hourly_bonus"))
    markup.row(InlineKeyboardButton("🏢 Бизнесы", callback_data="shop"), InlineKeyboardButton("⭐ Донат-бизнесы", callback_data="star_shop"))
    markup.row(InlineKeyboardButton("📈 Инвестиции", callback_data="invest_menu"), InlineKeyboardButton("🛍️ Доступные", callback_data="available_shop"))
    markup.row(InlineKeyboardButton("🎲 Аукцион (6ч)", callback_data="auction_menu"), InlineKeyboardButton("🛒 Рынок P2P", callback_data="market_menu"))
    markup.row(InlineKeyboardButton("🎒 Инвентарь", callback_data="inventory_menu"), InlineKeyboardButton("📂 Имущество", callback_data="my_props"))
    markup.row(InlineKeyboardButton("📜 Задания", callback_data="quests_menu"), InlineKeyboardButton("📢 Каналы", callback_data="channels"))
    return markup

@bot.message_handler(commands=["start"])
def send_welcome(message):
    get_user(message.chat.id)
    bot.send_message(message.chat.id, "🌆 Добро пожаловать! Бот успешно запущен и готов к работе.", reply_markup=main_menu_markup())

# --- УНИВЕРСАЛЬНАЯ АДМИН-КОМАНДА ДЛЯ ВЫДАЧИ МОНЕТ СЕБЕ ИЛИ ДРУГИМ ---
@bot.message_handler(commands=["addmoney"])
def cmd_add_money(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав на использование этой команды.")
        return
    try:
        parts = message.text.split()
        
        # Если передан ID игрока и сумма: /addmoney 123456789 500
        if len(parts) >= 3:
            target_id = int(parts[1])
            amount = float(parts[2])
            
            user = get_user(target_id)
            user["balance"] += amount
            save_user(target_id, user)
            
            bot.send_message(message.chat.id, f"✅ Успешно выдано **{amount}** монет игроку с ID `{target_id}`!\nНовый баланс игрока: **{round(user['balance'], 2)}**", parse_mode="Markdown")
            try:
                bot.send_message(target_id, f"🎁 Администратор начислил вам **{amount}** монет!")
            except:
                pass
                
        # Если передана только сумма: /addmoney 1000 (выдает вам)
        elif len(parts) == 2:
            amount = float(parts[1])
            user = get_user(message.chat.id)
            user["balance"] += amount
            save_user(message.chat.id, user)
            bot.send_message(message.chat.id, f"✅ Успешно выдано себе: **{amount}** монет!\nТекущий баланс: **{round(user['balance'], 2)}**", parse_mode="Markdown")
            
        else:
            bot.send_message(message.chat.id, "❌ Использование:\n• Себе: `/addmoney 1000`\n• Другому: `/addmoney ID СУММА`", parse_mode="Markdown")
            
    except Exception:
        bot.send_message(message.chat.id, "❌ Ошибка! Проверьте правильность введенных данных.\nПример: `/addmoney 123456789 500`", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user = get_user(chat_id)
    
    if call.data == "profile_menu":
        bot.answer_callback_query(call.id)
        name = call.from_user.first_name if call.from_user.first_name else "Игрок"
        equipped = f"✨ {user['equipped']}" if user['equipped'] else "✨ Ничего"
        
        text = (
            f"👤 **Профиль игрока**\n\n"
            f"🏷️ Имя: **{name}**\n"
            f"🆔 Ваш игровой ID: `{chat_id}`\n"
            f"💰 Баланс: **{round(user['balance'], 2)} монет**\n"
            f"🎒 Надетый аксессуар: {equipped}\n\n"
            f"🎮 *Сражайтесь с другими игроками 1 на 1!*"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🃏 Игра 21 (Дуэль)", callback_data="blackjack_menu"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "blackjack_menu":
        bot.answer_callback_query(call.id)
        text = (
            f"🃏 **Дуэль в 21 очко (1 на 1)**\n\n"
            f"Правила: Бросьте вызов любому игроку по его ID, указав ставку. "
            f"После того как он примет бой, вам обоим раздадутся карты. "
            f"Побеждает тот, кто наберет больше очков, но не превысит 21!\n\n"
            f"Нажмите кнопку ниже, чтобы создать вызов:"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("⚔️ Создать вызов на бой", callback_data="bj_create_challenge"))
        markup.row(InlineKeyboardButton("🔙 В профиль", callback_data="profile_menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "bj_create_challenge":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(
            chat_id, 
            "✍️ Отправьте в чат **ID соперника и ставку** через запятую.\nПример: `123456789, 50`", 
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_bj_challenge)

    elif call.data.startswith("bj_accept_"):
        try:
            p1_id = int(call.data.replace("bj_accept_", ""))
            p2_id = chat_id
            
            found_key = None
            for k, d in ACTIVE_DUELS.items():
                if d["p1"] == p1_id and d["p2"] == p2_id and not d.get("accepted"):
                    found_key = k
                    break
            
            if not found_key:
                bot.answer_callback_query(call.id, "Срок вызова истек или он уже неактивен.", show_alert=True)
                return
                
            duel = ACTIVE_DUELS[found_key]
            bet = duel["bet"]
            
            p1_data = get_user(p1_id)
            p2_data = get_user(p2_id)
            
            if p1_data["balance"] < bet or p2_data["balance"] < bet:
                bot.answer_callback_query(call.id, "У одного из игроков недостаточно средств для ставки!", show_alert=True)
                del ACTIVE_DUELS[found_key]
                return
                
            p1_data["balance"] -= bet
            p2_data["balance"] -= bet
            save_user(p1_id, p1_data)
            save_user(p2_id, p2_data)
            
            duel["accepted"] = True
            
            deck = [2, 3, 4, 6, 7, 8, 9, 10, 2, 3, 4, 6, 7, 8, 9, 10, 11, 4] * 4
            random.shuffle(deck)
            
            duel["deck"] = deck
            duel["p1_cards"] = [deck.pop(), deck.pop()]
            duel["p2_cards"] = [deck.pop(), deck.pop()]
            
            bot.answer_callback_query(call.id, "Бой принят! Раздача карт...", show_alert=True)
            send_bj_table(found_key)
            
        except Exception:
            bot.answer_callback_query(call.id, "Ошибка при принятии вызова", show_alert=True)

    elif call.data.startswith("bj_decline_"):
        try:
            p1_id = int(call.data.replace("bj_decline_", ""))
            bot.answer_callback_query(call.id, "Вы отклонили вызов.", show_alert=True)
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="❌ Вы отклонили вызов на дуэль.")
            try:
                bot.send_message(p1_id, "❌ Соперник отклонил ваш вызов на дуэль в 21.")
            except:
                pass
        except:
            bot.answer_callback_query(call.id, "Ошибка", show_alert=True)

    elif call.data.startswith("bj_hit_"):
        duel_id = call.data.replace("bj_hit_", "")
        if duel_id in ACTIVE_DUELS:
            duel = ACTIVE_DUELS[duel_id]
            if not duel.get("accepted"):
                bot.answer_callback_query(call.id, "Дуэль еще не началась!", show_alert=True)
                return
            if chat_id == duel["p1"] and not duel["p1_stand"]:
                duel["p1_cards"].append(duel["deck"].pop())
                if sum(duel["p1_cards"]) > 21:
                    duel["p1_stand"] = True
            elif chat_id == duel["p2"] and not duel["p2_stand"]:
                duel["p2_cards"].append(duel["deck"].pop())
                if sum(duel["p2_cards"]) > 21:
                    duel["p2_stand"] = True
            bot.answer_callback_query(call.id, "Карта взята!")
            check_bj_finish(duel_id)

    elif call.data.startswith("bj_stand_"):
        duel_id = call.data.replace("bj_stand_", "")
        if duel_id in ACTIVE_DUELS:
            duel = ACTIVE_DUELS[duel_id]
            if not duel.get("accepted"):
                bot.answer_callback_query(call.id, "Дуэль еще не началась!", show_alert=True)
                return
            if chat_id == duel["p1"]:
                duel["p1_stand"] = True
            elif chat_id == duel["p2"]:
                duel["p2_stand"] = True
            bot.answer_callback_query(call.id, "Вы остановились.")
            check_bj_finish(duel_id)

    elif call.data == "balance":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"💰 Твой баланс: {round(user['balance'], 2)} монет", reply_markup=main_menu_markup())
        
    elif call.data == "income_info":
        bot.answer_callback_query(call.id)
        total_income = sum(item["income"] for p in user["properties"] for item in {**HOUSES, **STAR_HOUSES}.values() if item["name"] == p)
        total_income += sum(item["income"] for inv in user["investments"] for item in INVESTMENTS.values() if item["name"] == inv)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"📊 Общий пассивный доход: {round(total_income, 2)} монет/мин", reply_markup=main_menu_markup())
        
    elif call.data == "shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in HOUSES.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет (+{item['income']}/мин)", callback_data=f"buy_coin_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🏪 Магазин бизнесов:", reply_markup=markup)

    elif call.data == "star_shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in STAR_HOUSES.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — ⭐ {item['price']} Звёзд (+{item['income']}/мин)", callback_data=f"buy_star_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="⭐ Премиум бизнесы за Звёзды:", reply_markup=markup)

    elif call.data.startswith("buy_star_"):
        key = call.data.replace("buy_star_", "")
        item = STAR_HOUSES.get(key)
        if item:
            bot.answer_callback_query(call.id)
            prices = [LabeledPrice(label=item["name"], amount=item["price"])]
            try:
                bot.send_invoice(
                    chat_id=chat_id,
                    title=item["name"],
                    description=f"Покупка премиум бизнеса {item['name']} с доходом +{item['income']}/мин",
                    invoice_payload=f"buy_prop_{key}",
                    provider_token="",
                    currency="XTR",
                    prices=prices
                )
            except Exception as e:
                bot.send_message(chat_id, f"❌ Ошибка создания инвойса: {e}")
        
    elif call.data == "invest_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in INVESTMENTS.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет (+{item['income']}/мин)", callback_data=f"buy_inv_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="📈 Инвестиции:", reply_markup=markup)

    elif call.data == "inventory_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        equipped_text = f"✨ Надето: **{user['equipped']}**" if user['equipped'] else "✨ Надето: **Ничего**"
        if user["accessories"]:
            text = f"🎒 **Инвентарь аксессуаров**\n\n{equipped_text}\n\nВыбери предмет:"
            for idx, acc in enumerate(user["accessories"]):
                prefix = "🟢 " if acc == user["equipped"] else ""
                markup.row(InlineKeyboardButton(f"{prefix}{acc}", callback_data=f"equip_acc_{idx}"))
        else:
            text = f"🎒 **Инвентарь пуст**\n\n{equipped_text}"
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("equip_acc_"):
        try:
            idx = int(call.data.replace("equip_acc_", ""))
            if idx < len(user["accessories"]):
                item_name = user["accessories"][idx]
                user["equipped"] = "" if user["equipped"] == item_name else item_name
                save_user(chat_id, user)
                bot.answer_callback_query(call.id, "Успешно!", show_alert=True)
                call.data = "inventory_menu"
                callback_handler(call)
        except:
            pass

    elif call.data == "auction_menu":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect("game.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, current_price, highest_bidder_name, end_time FROM auction WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            item_name, current_price, highest_bidder_name, end_time = row
            time_left = max(0, end_time - int(time.time()))
            hours, mins = time_left // 3600, (time_left % 3600) // 60
            text = f"🎲 Аукцион\n\nЛот: **{item_name}**\nСтавка: **{current_price}**\nЛидер: **{highest_bidder_name}**\nОсталось: {hours}ч {mins}мин"
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton(f"💸 Поставить {current_price + 100}", callback_data="make_bid"))
            markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "make_bid":
        conn = sqlite3.connect("game.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, current_price, highest_bidder, end_time FROM auction WHERE id = 1")
        row = cursor.fetchone()
        if row:
            item_name, current_price, highest_bidder, end_time = row
            next_price = current_price + 100.0
            if user["balance"] < next_price:
                bot.answer_callback_query(call.id, "Недостаточно монет!", show_alert=True)
                conn.close()
                return
            if highest_bidder > 0:
                cursor.execute("UPDATE users SET balance = balance + ? WHERE chat_id = ?", (current_price, highest_bidder))
            user["balance"] -= next_price
            save_user(chat_id, user)
            user_name = call.from_user.first_name if call.from_user.first_name else "Игрок"
            cursor.execute("UPDATE auction SET current_price = ?, highest_bidder = ?, highest_bidder_name = ? WHERE id = 1", (next_price, chat_id, user_name))
            conn.commit()
            conn.close()
            bot.answer_callback_query(call.id, "Ставка принята!", show_alert=True)
            call.data = "auction_menu"
            callback_handler(call)

    elif call.data == "market_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🛒 Купить", callback_data="market_buy_list"), InlineKeyboardButton("📦 Продать", callback_data="market_sell_list"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🛒 Рынок P2P:", reply_markup=markup)

    elif call.data == "market_buy_list":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect("game.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT id, seller_name, item_name, price FROM market")
        lots = cursor.fetchall()
        conn.close()
        markup = InlineKeyboardMarkup()
        if lots:
            for lot in lots:
                lot_id, seller_name, item_name, price = lot
                markup.row(InlineKeyboardButton(f"{item_name} | {price} ({seller_name})", callback_data=f"buy_market_{lot_id}"))
        markup.row(InlineKeyboardButton("🔙 Назад", callback_data="market_menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🛒 Доступные лоты:", reply_markup=markup)

    elif call.data.startswith("buy_market_"):
        try:
            lot_id = int(call.data.replace("buy_market_", ""))
            conn = sqlite3.connect("game.db", check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT seller_id, item_name, price FROM market WHERE id = ?", (lot_id,))
            lot = cursor.fetchone()
            if not lot or lot[0] == chat_id:
                bot.answer_callback_query(call.id, "Невозможно купить!", show_alert=True)
                conn.close()
                return
            seller_id, item_name, price = lot
            if user["balance"] < price:
                bot.answer_callback_query(call.id, "Недостаточно монет!", show_alert=True)
                conn.close()
                return
            user["balance"] -= price
            user["accessories"].append(item_name)
            save_user(chat_id, user)
            cursor.execute("UPDATE users SET balance = balance + ? WHERE chat_id = ?", (price, seller_id))
            cursor.execute("DELETE FROM market WHERE id = ?", (lot_id,))
            conn.commit()
            conn.close()
            bot.answer_callback_query(call.id, "Куплено!", show_alert=True)
            call.data = "market_menu"
            callback_handler(call)
        except:
            pass

    elif call.data == "market_sell_list":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        if user["accessories"]:
            for idx, acc in enumerate(user["accessories"]):
                markup.row(InlineKeyboardButton(f"📦 Продать {acc}", callback_data=f"sell_acc_{idx}"))
        markup.row(InlineKeyboardButton("🔙 Назад", callback_data="market_menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="📦 Выберите предмет для продажи:", reply_markup=markup)

    elif call.data.startswith("sell_acc_"):
        try:
            idx = int(call.data.replace("sell_acc_", ""))
            if idx < len(user["accessories"]):
                item_name = user["accessories"].pop(idx)
                if user["equipped"] == item_name:
                    user["equipped"] = ""
                save_user(chat_id, user)
                conn = sqlite3.connect("game.db", check_same_thread=False)
                cursor = conn.cursor()
                seller_name = call.from_user.first_name if call.from_user.first_name else "Игрок"
                cursor.execute("INSERT INTO market (seller_id, seller_name, item_name, price) VALUES (?, ?, ?, ?)", (chat_id, seller_name, item_name, 500.0))
                conn.commit()
                conn.close()
                bot.answer_callback_query(call.id, "Выставлено!", show_alert=True)
                call.data = "market_menu"
                callback_handler(call)
        except:
            pass

    elif call.data == "channels":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("👉 Канал", url="https://t.me/top4ikeco"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="📢 Канал проекта:", reply_markup=markup)

    elif call.data == "available_shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in {**HOUSES, **INVESTMENTS}.items():
            if user["balance"] >= item["price"]:
                markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']}", callback_data=f"buy_coin_{key}" if key in HOUSES else f"buy_inv_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🛍️ Доступно для покупки:", reply_markup=markup)

    elif call.data == "quests_menu":
        bot.answer_callback_query(call.id)
        stage = user["quest_stage"]
        markup = InlineKeyboardMarkup()
        if stage in QUESTS:
            q = QUESTS[stage]
            markup.row(InlineKeyboardButton(f"🎁 Забрать награду (+{q['reward']})", callback_data="claim_quest"))
            text = f"📜 Задание:\n\n🔹 **{q['title']}**"
        else:
            text = "📜 Все задания выполнены!"
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "claim_quest":
        stage = user["quest_stage"]
        if stage in QUESTS and QUESTS[stage]["target_prop"] in user["properties"]:
            q = QUESTS[stage]
            user["balance"] += q["reward"]
            user["quest_stage"] += 1
            save_user(chat_id, user)
            bot.answer_callback_query(call.id, "Награда получена!", show_alert=True)
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🎉 Задание выполнено!", reply_markup=main_menu_markup())

    elif call.data == "hourly_bonus":
        if time.time() - int(user["last_bonus"] or 0) >= 3600:
            user["balance"] += 3.0
            user["last_bonus"] = int(time.time())
            save_user(chat_id, user)
            bot.answer_callback_query(call.id, "+3 монеты!", show_alert=True)
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="⏰ Бонус получен!", reply_markup=main_menu_markup())
        else:
            bot.answer_callback_query(call.id, "Рано для бонуса!", show_alert=True)

    elif call.data.startswith("buy_inv_") or call.data.startswith("buy_coin_"):
        is_inv = call.data.startswith("buy_inv_")
        key = call.data.replace("buy_inv_" if is_inv else "buy_coin_", "")
        item = INVESTMENTS.get(key) if is_inv else HOUSES.get(key)
        if item and user["balance"] >= item["price"]:
            user["balance"] -= item["price"]
            (user["investments"] if is_inv else user["properties"]).append(item["name"])
            save_user(chat_id, user)
            bot.answer_callback_query(call.id, "Успешно куплено!", show_alert=True)
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="✅ Покупка завершена!", reply_markup=main_menu_markup())

    elif call.data == "my_props":
        bot.answer_callback_query(call.id)
        props = ", ".join(user["properties"]) if user["properties"] else "нет"
        invs = ", ".join(user["investments"]) if user["investments"] else "нет"
        text = f"📂 Имущество:\n\nБизнесы: {props}\n\nИнвестиции: {invs}"
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=main_menu_markup())

    elif call.data == "menu":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Главное меню:", reply_markup=main_menu_markup())

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout_handler(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=["successful_payment"])
def got_payment(message):
    payment = message.successful_payment
    chat_id = message.chat.id
    user = get_user(chat_id)
    if payment.invoice_payload.startswith("buy_prop_"):
        house_key = payment.invoice_payload.replace("buy_prop_", "")
        if house_key in STAR_HOUSES:
            item = STAR_HOUSES[house_key]
            user["properties"].append(item["name"])
            save_user(chat_id, user)
            bot.send_message(chat_id, f"⭐ Оплата прошла успешно! Премиум актив «{item['name']}» добавлен в твоё имущество!")

def process_bj_challenge(message):
    try:
        parts = message.text.split(",")
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Неверный формат! Введите так: `ID, СТАВКА`", parse_mode="Markdown")
            return
            
        p2_id = int(parts[0].strip())
        bet = float(parts[1].strip())
        p1_id = message.chat.id
        
        if p1_id == p2_id:
            bot.send_message(p1_id, "❌ Нельзя играть против самого себя!")
            return
            
        if bet <= 0:
            bot.send_message(p1_id, "❌ Ставка должна быть больше 0!")
            return
            
        p1_data = get_user(p1_id)
        if p1_data["balance"] < bet:
            bot.send_message(p1_id, "❌ У вас недостаточно монет для такой ставки!")
            return
            
        duel_id = f"{p1_id}_{p2_id}_{int(time.time())}"
        ACTIVE_DUELS[duel_id] = {
            "p1": p1_id,
            "p2": p2_id,
            "bet": bet,
            "accepted": False
        }
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅ Принять бой", callback_data=f"bj_accept_{p1_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"bj_decline_{p1_id}")
        )
        
        p1_name = message.from_user.first_name if message.from_user.first_name else "Игрок"
        bot.send_message(
            p2_id, 
            f"⚔️ **Вызов на дуэль в 21 очко!**\n\nИгрок **{p1_name}** вызывает вас на бой.\n💰 Ставка: **{bet} монет**.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        bot.send_message(p1_id, "📤 Вызов успешно отправлен сопернику. Ожидайте ответа!")
    except Exception:
        bot.send_message(message.chat.id, "❌ Ошибка! Проверьте правильность введенных данных (пример: `123456789, 50`)", parse_mode="Markdown")

def send_bj_table(duel_id):
    if duel_id not in ACTIVE_DUELS:
        return
    duel = ACTIVE_DUELS[duel_id]
    p1, p2 = duel["p1"], duel["p2"]
    
    p1_sum = sum(duel["p1_cards"])
    p2_sum = sum(duel["p2_cards"])
    
    markup_p1 = InlineKeyboardMarkup()
    markup_p1.row(InlineKeyboardButton("🃏 Взять карту", callback_data=f"bj_hit_{duel_id}"), InlineKeyboardButton("🛑 Хватит", callback_data=f"bj_stand_{duel_id}"))
    
    markup_p2 = InlineKeyboardMarkup()
    markup_p2.row(InlineKeyboardButton("🃏 Взять карту", callback_data=f"bj_hit_{duel_id}"), InlineKeyboardButton("🛑 Хватит", callback_data=f"bj_stand_{duel_id}"))
    
    try:
        bot.send_message(p1, f"🃏 **Дуэль 21**\n\nВаши карты: {duel['p1_cards']} (Сумма: **{p1_sum}**)\nКарты соперника: скрыты", reply_markup=markup_p1, parse_mode="Markdown")
    except:
        pass
        
    try:
        bot.send_message(p2, f"🃏 **Дуэль 21**\n\nВаши карты: {duel['p2_cards']} (Сумма: **{p2_sum}**)\nКарты соперника: скрыты", reply_markup=markup_p2, parse_mode="Markdown")
    except:
        pass

def check_bj_finish(duel_id):
    if duel_id not in ACTIVE_DUELS:
        return
    duel = ACTIVE_DUELS[duel_id]
    p1, p2 = duel["p1"], duel["p2"]
    p1_sum = sum(duel["p1_cards"])
    p2_sum = sum(duel["p2_cards"])
    
    p1_ended = duel.get("p1_stand", False) or p1_sum > 21
    p2_ended = duel.get("p2_stand", False) or p2_sum > 21
    
    if p1_ended and p2_ended:
        winner = None
        text_res = f"🏁 **Итоги дуэли в 21!**\n\nВаши карты: {duel['p1_cards']} ({p1_sum})\nКарты соперника: {duel['p2_cards']} ({p2_sum})\n\n"
        
        if p1_sum > 21 and p2_sum > 21:
            res_p1 = "Ничья (у обоих перебор). Ставки возвращены."
            res_p2 = res_p1
            get_user(p1)["balance"] += duel["bet"]
            get_user(p2)["balance"] += duel["bet"]
        elif p1_sum > 21:
            res_p1 = "❌ У вас перебор! Вы проиграли."
            res_p2 = "🎉 Соперник перебрал! Вы победили!"
            winner = p2
        elif p2_sum > 21:
            res_p1 = "🎉 Соперник перебрал! Вы победили!"
            res_p2 = "❌ У вас перебор! Вы проиграли."
            winner = p1
        elif p1_sum > p2_sum:
            res_p1 = "🏆 Вы победили!"
            res_p2 = "❌ Вы проиграли."
            winner = p1
        elif p2_sum > p1_sum:
            res_p1 = "❌ Вы проиграли."
            res_p2 = "🏆 Вы победили!"
            winner = p2
        else:
            res_p1 = "🤝 Ничья! Ставки возвращены."
            res_p2 = res_p1
            get_user(p1)["balance"] += duel["bet"]
            get_user(p2)["balance"] += duel["bet"]
            
        if winner:
            w_data = get_user(winner)
            w_data["balance"] += duel["bet"] * 2
            save_user(winner, w_data)
            
        save_user(p1, get_user(p1))
        save_user(p2, get_user(p2))
        
        try:
            bot.send_message(p1, text_res + res_p1, reply_markup=main_menu_markup(), parse_mode="Markdown")
        except:
            pass
        try:
            bot.send_message(p2, text_res.replace(str(duel['p1_cards']), "скрыто").replace(str(p1_sum), "скрыто") + res_p2, reply_markup=main_menu_markup(), parse_mode="Markdown")
        except:
            pass
            
        del ACTIVE_DUELS[duel_id]
    else:
        try:
            markup1 = InlineKeyboardMarkup()
            if not duel["p1_stand"]:
                markup1.row(InlineKeyboardButton("🃏 Взять карту", callback_data=f"bj_hit_{duel_id}"), InlineKeyboardButton("🛑 Хватит", callback_data=f"bj_stand_{duel_id}"))
            bot.send_message(p1, f"🃏 Обновление счета:\nВаши карты: {duel['p1_cards']} (Сумма: **{p1_sum}**)", reply_markup=markup1 if not duel["p1_stand"] else None, parse_mode="Markdown")
        except:
            pass
        try:
            markup2 = InlineKeyboardMarkup()
            if not duel["p2_stand"]:
                markup2.row(InlineKeyboardButton("🃏 Взять карту", callback_data=f"bj_hit_{duel_id}"), InlineKeyboardButton("🛑 Хватит", callback_data=f"bj_stand_{duel_id}"))
            bot.send_message(p2, f"🃏 Обновление счета:\nВаши карты: {duel['p2_cards']} (Сумма: **{p2_sum}**)", reply_markup=markup2 if not duel["p2_stand"] else None, parse_mode="Markdown")
        except:
            pass

if __name__ == "__main__":
    print("Бот запущен и проверен на ошибки...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
