import time
import threading
import sqlite3
import random
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice

TOKEN = "8631846961:AAGpjWYBTBugvefFkiWBSucihBEZBthlY2M"
bot = telebot.TeleBot(TOKEN)

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
            last_bonus INTEGER DEFAULT 0,
            quest_stage INTEGER DEFAULT 1,
            quest_claimed INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user(chat_id):
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, properties, investments, last_bonus, quest_stage, quest_claimed FROM users WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (chat_id, balance, properties, investments, last_bonus, quest_stage, quest_claimed) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                       (chat_id, 15.0, "", "", 0, 1, 0))
        conn.commit()
        user_data = {"balance": 15.0, "properties": [], "investments": [], "last_bonus": 0, "quest_stage": 1, "quest_claimed": 0}
    else:
        props = row[1].split(",") if row[1] else []
        invs = row[2].split(",") if row[2] else []
        user_data = {"balance": row[0], "properties": props, "investments": invs, "last_bonus": row[3], "quest_stage": row[4], "quest_claimed": row[5]}
    conn.close()
    return user_data

def save_user(chat_id, user_data):
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    props_str = ",".join(user_data["properties"])
    invs_str = ",".join(user_data["investments"])
    cursor.execute("UPDATE users SET balance = ?, properties = ?, investments = ?, last_bonus = ?, quest_stage = ?, quest_claimed = ? WHERE chat_id = ?",
                   (user_data["balance"], props_str, invs_str, user_data["last_bonus"], user_data["quest_stage"], user_data["quest_claimed"], chat_id))
    conn.commit()
    conn.close()

# --- ОБЫЧНЫЕ БИЗНЕСЫ ---
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

# --- ДОНАТ-БИЗНЕСЫ ЗА ЗВЕЗДЫ ---
STAR_HOUSES = {
    "star_cafe": {"name": "⭐ Звездная Кофейня", "price": 5, "income": 602000.0},
    "star_1": {"name": "💎 Звездная IT-Корпорация", "price": 15, "income": 2102000.0},
    "star_2": {"name": "🚀 Звездный Космопорт", "price": 40, "income": 7202000.0},
    "star_3": {"name": "🛰️ Звездная Спутниковая связь", "price": 100, "income": 27002000.0},
    "star_4": {"name": "🌌 Межгалактический Звездный Банк", "price": 250, "income": 90002000.0}
}

# --- ИНВЕСТИЦИИ ---
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

# Фоновый поток начислений дохода (раз в минуту)
def income_loop():
    while True:
        time.sleep(60)
        conn = sqlite3.connect("game.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, balance, properties, investments FROM users")
        rows = cursor.fetchall()
        
        for row in rows:
            chat_id = row[0]
            balance = row[1]
            props = row[2].split(",") if row[2] else []
            invs = row[3].split(",") if row[3] else []
            
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

threading.Thread(target=income_loop, daemon=True).start()

def main_menu_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("💰 Баланс", callback_data="balance"), InlineKeyboardButton("📊 Доход", callback_data="income_info"))
    markup.row(InlineKeyboardButton("🏢 Бизнесы (20 шт.)", callback_data="shop"), InlineKeyboardButton("⭐ Донат-бизнесы", callback_data="star_shop"))
    markup.row(InlineKeyboardButton("📈 Инвестиции", callback_data="invest_menu"), InlineKeyboardButton("🛍️ Доступные", callback_data="available_shop"))
    markup.row(InlineKeyboardButton("🎰 Казино", callback_data="casino_menu"), InlineKeyboardButton("📜 Задания", callback_data="quests_menu"))
    markup.row(InlineKeyboardButton("📂 Мое имущество", callback_data="my_props"), InlineKeyboardButton("⏰ Бонус (3 монеты)", callback_data="hourly_bonus"))
    markup.row(InlineKeyboardButton("📢 Каналы", callback_data="channels"))
    return markup

@bot.message_handler(commands=["start"])
def send_welcome(message):
    get_user(message.chat.id)
    bot.send_message(message.chat.id, "🌆 Добро пожаловать! Минимальная ставка в казино теперь 500 монет.", reply_markup=main_menu_markup())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user = get_user(chat_id)
    
    if call.data == "balance":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"💰 Твой баланс: {round(user['balance'], 2)} монет",
            reply_markup=main_menu_markup()
        )
        
    elif call.data == "income_info":
        bot.answer_callback_query(call.id)
        total_income = 0.0
        for p in user["properties"]:
            for item in {**HOUSES, **STAR_HOUSES}.values():
                if item["name"] == p:
                    total_income += item["income"]
        for inv in user["investments"]:
            for item in INVESTMENTS.values():
                if item["name"] == inv:
                    total_income += item["income"]
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"📊 Твой общий пассивный доход: {round(total_income, 2)} монет в минуту",
            reply_markup=main_menu_markup()
        )
        
    elif call.data == "shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in HOUSES.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет (+{item['income']}/мин)", callback_data=f"buy_coin_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🏪 Магазин бизнесов (20 уровней):", reply_markup=markup)

    elif call.data == "star_shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in STAR_HOUSES.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — ⭐ {item['price']} Звёзд (+{item['income']}/мин)", callback_data=f"buy_star_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="⭐ Премиум бизнесы за Звёзды:", reply_markup=markup)
        
    elif call.data == "invest_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in INVESTMENTS.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет (+{item['income']}/мин)", callback_data=f"buy_inv_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="📈 Инвестиции:", reply_markup=markup)

    elif call.data == "casino_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🎲 Бросить кости (500 монет)", callback_data="casino_dice"),
            InlineKeyboardButton("🪙 Орёл и Решка (500 монет)", callback_data="casino_coin")
        )
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="🎰 Добро пожаловать в Казино!\n\nМинимальная ставка: 500 монет.",
            reply_markup=markup
        )

    elif call.data == "casino_dice":
        bet = 500.0
        if user["balance"] < bet:
            bot.answer_callback_query(call.id, "Недостаточно монет для ставки (нужно 500)!", show_alert=True)
            return
        
        user["balance"] -= bet
        player_roll = random.randint(1, 6)
        bot_roll = random.randint(1, 6)
        
        if player_roll > bot_roll:
            win_amount = bet * 2
            user["balance"] += win_amount
            result_text = f"🎉 Ты победил!\nТвой бросок: {player_roll} | Дилер: {bot_roll}\nВыигрыш: +{win_amount} монет!"
        elif player_roll < bot_roll:
            result_text = f"😢 Ты проиграл...\nТвой бросок: {player_roll} | Дилер: {bot_roll}\nПотеряно: {bet} монет."
        else:
            user["balance"] += bet
            result_text = f"🤝 Ничья!\nТвой бросок: {player_roll} | Дилер: {bot_roll}\nСтавка возвращена на баланс."
            
        save_user(chat_id, user)
        bot.answer_callback_query(call.id)
        
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🎲 Сыграть еще раз", callback_data="casino_dice"))
        markup.row(InlineKeyboardButton("🔙 В меню казино", callback_data="casino_menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=result_text, reply_markup=markup)

    elif call.data == "casino_coin":
        bet = 500.0
        if user["balance"] < bet:
            bot.answer_callback_query(call.id, "Недостаточно монет для ставки (нужно 500)!", show_alert=True)
            return
            
        user["balance"] -= bet
        outcome = random.choice(["Орёл", "Решка"])
        won = random.choice([True, False])
        
        if won:
            win_amount = bet * 2
            user["balance"] += win_amount
            result_text = f"🪙 Выпало: {outcome}!\n🎉 Удача на твоей стороне! Выигрыш: +{win_amount} монет!"
        else:
            result_text = f"🪙 Выпало: {outcome}!\n😢 К сожалению, ставка сгорела. Потеряно: {bet} монет."
            
        save_user(chat_id, user)
        bot.answer_callback_query(call.id)
        
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🪙 Крутить еще", callback_data="casino_coin"))
        markup.row(InlineKeyboardButton("🔙 В меню казино", callback_data="casino_menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=result_text, reply_markup=markup)

    elif call.data == "channels":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("👉 Перейти в канал", url="https://t.me/top4ikeco"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="📢 Перейдите в основной канал @top4ikeco, чтобы быть в курсе всех новостей и обновлений!",
            reply_markup=markup
        )

    elif call.data == "available_shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        found = False
        
        for key, item in HOUSES.items():
            if user["balance"] >= item["price"]:
                markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет (+{item['income']}/мин)", callback_data=f"buy_coin_{key}"))
                found = True
                
        for key, item in INVESTMENTS.items():
            if user["balance"] >= item["price"]:
                markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет (+{item['income']}/мин)", callback_data=f"buy_inv_{key}"))
                found = True
                
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        
        if found:
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"🛍️ Доступно для покупки на твой баланс ({round(user['balance'], 2)} монет):", reply_markup=markup)
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"😢 На балансе ({round(user['balance'], 2)} монет) пока недостаточно средств.", reply_markup=markup)
        
    elif call.data == "quests_menu":
        bot.answer_callback_query(call.id)
        stage = user["quest_stage"]
        markup = InlineKeyboardMarkup()
        if stage in QUESTS:
            q = QUESTS[stage]
            markup.row(InlineKeyboardButton(f"🎁 Забрать награду (+{q['reward']} монет)", callback_data="claim_quest"))
            text = f"📜 Текущее задание:\n\n🔹 **{q['title']}**\n🏆 Награда: {q['reward']} монет"
        else:
            text = "📜 Все задания выполнены!"
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "claim_quest":
        stage = user["quest_stage"]
        if stage in QUESTS:
            q = QUESTS[stage]
            if q["target_prop"] in user["properties"]:
                user["balance"] += q["reward"]
                user["quest_stage"] += 1
                save_user(chat_id, user)
                bot.answer_callback_query(call.id, f"Награда получена (+{q['reward']} монет)!", show_alert=True)
                bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"🎉 Задание выполнено! Получено {q['reward']} монет.", reply_markup=main_menu_markup())
            else:
                bot.answer_callback_query(call.id, f"У тебя еще не куплено: {q['target_prop']}!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Все задания уже выполнены!", show_alert=True)
        
    elif call.data == "hourly_bonus":
        current_time = int(time.time())
        last_b = int(user["last_bonus"] or 0)
        cooldown = 3600
        
        if current_time - last_b >= cooldown:
            user["balance"] += 3.0
            user["last_bonus"] = current_time
            save_user(chat_id, user)
            bot.answer_callback_query(call.id, "Вы успешно получили 3 монеты!", show_alert=True)
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="⏰ Ежечасовой бонус успешно получен: +3 монеты на баланс!",
                reply_markup=main_menu_markup()
            )
        else:
            time_left = cooldown - (current_time - last_b)
            minutes_left = max(1, int(time_left // 60))
            bot.answer_callback_query(call.id, f"Бонус будет доступен через {minutes_left} мин.", show_alert=True)
        
    elif call.data.startswith("buy_inv_"):
        inv_key = call.data.replace("buy_inv_", "")
        if inv_key in INVESTMENTS:
            item = INVESTMENTS[inv_key]
            if user["balance"] >= item["price"]:
                user["balance"] -= item["price"]
                user["investments"].append(item["name"])
                save_user(chat_id, user)
                bot.answer_callback_query(call.id, "Успешно куплено!", show_alert=True)
                bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"✅ Ты успешно купил инвестицию «{item['name']}»!", reply_markup=main_menu_markup())
            else:
                bot.answer_callback_query(call.id, "Недостаточно монет!", show_alert=True)
            
    elif call.data.startswith("buy_coin_"):
        house_key = call.data.replace("buy_coin_", "")
        if house_key in HOUSES:
            item = HOUSES[house_key]
            if user["balance"] >= item["price"]:
                user["balance"] -= item["price"]
                user["properties"].append(item["name"])
                save_user(chat_id, user)
                bot.answer_callback_query(call.id, "Успешно куплено!", show_alert=True)
                bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"🎉 Поздравляем с покупкой: {item['name']}!", reply_markup=main_menu_markup())
            else:
                bot.answer_callback_query(call.id, "Недостаточно монет!", show_alert=True)
            
    elif call.data.startswith("buy_star_"):
        house_key = call.data.replace("buy_star_", "")
        if house_key in STAR_HOUSES:
            item = STAR_HOUSES[house_key]
            bot.answer_callback_query(call.id)
            prices = [LabeledPrice(label=item['name'], amount=item['price'])]
            bot.send_invoice(
                chat_id=chat_id,
                title=item['name'],
                description=f"Купить премиум актив «{item['name']}» за Telegram Stars",
                invoice_payload=f"buy_prop_{house_key}",
                provider_token="",
                currency="XTR",
                prices=prices
            )
            
    elif call.data == "my_props":
        bot.answer_callback_query(call.id)
        props = ", ".join(user["properties"]) if user["properties"] else "нет"
        invs = ", ".join(user["investments"]) if user["investments"] else "нет"
        text = f"📂 Твое имущество:\n\n🌐 Бизнесы и Недвижимость:\n{props}\n\n📈 Инвестиции:\n{invs}"
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
            bot.send_message(chat_id, f"⭐ Оплата прошла успешно! Премиум актив «{item['name']}» добавлен в твоё имущество и приносит {item['income']} монет в минуту!")

if __name__ == "__main__":
    print("Бот с минимальной ставкой 500 монет запущен...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
