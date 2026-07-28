import time
import logging
import sqlite3
import random
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8631846961:AAGpjWYBTBugvefFkiWBSucihBEZBthlY2M"
ADMIN_ID = 5107814486

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = telebot.TeleBot(TOKEN)

ACTIVE_GAMES_21 = {}

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
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, properties, investments, accessories, equipped_accessory, last_bonus, quest_stage, quest_claimed FROM users WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (chat_id, balance, properties, investments, accessories, equipped_accessory, last_bonus, quest_stage, quest_claimed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       (chat_id, 15.0, "", "", "", "", 0, 1, 0))
        conn.commit()
        user_data = {
            "balance": 15.0, 
            "properties": [], 
            "investments": [], 
            "accessories": [], 
            "equipped": ""
        }
    else:
        user_data = {
            "balance": row[0],
            "properties": row[1].split(",") if row[1] else [],
            "investments": row[2].split(",") if row[2] else [],
            "accessories": row[3].split(",") if row[3] else [],
            "equipped": row[4] if row[4] else ""
        }
    conn.close()
    return user_data

def save_user(chat_id, user_data):
    conn = sqlite3.connect("game.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = ?, properties = ?, investments = ?, accessories = ?, equipped_accessory = ? WHERE chat_id = ?",
                   (user_data["balance"], ",".join(user_data["properties"]), ",".join(user_data["investments"]), 
                    ",".join(user_data["accessories"]), user_data["equipped"], chat_id))
    conn.commit()
    conn.close()

# --- ЛОГИКА ИГРЫ 21 ---
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

def main_menu_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("👤 Профиль", callback_data="profile_menu"), InlineKeyboardButton("💰 Баланс", callback_data="balance"))
    markup.row(InlineKeyboardButton("🎲 Сыграть в 21", callback_data="start_21"))
    markup.row(InlineKeyboardButton("🎒 Инвентарь", callback_data="inventory_menu"), InlineKeyboardButton("🎁 Получить бонус", callback_data="get_test_item"))
    return markup

@bot.message_handler(commands=["start"])
def send_welcome(message):
    get_user(message.chat.id)
    bot.send_message(message.chat.id, "🌆 Добро пожаловать! Бот работает.", reply_markup=main_menu_markup())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user_data = get_user(chat_id)

    if call.data == "profile_menu" or call.data == "menu":
        bot.answer_callback_query(call.id)
        equipped_str = f"✨ {user_data['equipped']}" if user_data['equipped'] else "✨ Ничего"
        text = f"👤 **Профиль**\n\n🆔 ID: `{chat_id}`\n💰 Баланс: **{round(user_data['balance'], 2)} монет**\nНадето: {equipped_str}"
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=main_menu_markup(), parse_mode="Markdown")

    elif call.data == "balance":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"💰 Баланс: {round(user_data['balance'], 2)} монет", reply_markup=main_menu_markup())

    # --- ТЕСТОВАЯ КНОПКА: ВЫДАТЬ АКСЕССУАР ДЛЯ ПРОВЕРКИ ИНВЕНТАРЯ ---
    elif call.data == "get_test_item":
        test_items = ["👑 Золотая корона", "🗡️ Меч самурая", "⚡ Энергетик", "🕶️ Крутые очки"]
        item = random.choice(test_items)
        if item not in user_data["accessories"]:
            user_data["accessories"].append(item)
            save_user(chat_id, user_data)
            bot.answer_callback_query(call.id, f"🎁 В инвентарь добавлен аксессуар: {item}!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Этот аксессуар у вас уже есть!", show_alert=True)
        callback_handler(call) # Возврат в меню

    # --- ИНВЕНТАРЬ И АКСЕССУАРЫ ---
    elif call.data == "inventory_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        equipped_text = f"✨ Надето: **{user_data['equipped']}**" if user_data['equipped'] else "✨ Надето: **Ничего**"
        
        if user_data["accessories"]:
            text = f"🎒 **Ваш инвентарь аксессуаров**\n\n{equipped_text}\n\nНажмите на предмет, чтобы надеть или снять его:"
            for idx, acc in enumerate(user_data["accessories"]):
                prefix = "🟢 [Надето] " if acc == user_data["equipped"] else ""
                markup.row(InlineKeyboardButton(f"{prefix}{acc}", callback_data=f"equip_acc_{idx}"))
        else:
            text = f"🎒 **Инвентарь пуст**\n\n{equipped_text}\n\n(Нажмите кнопку «Получить бонус», чтобы получить тестовые предметы)"
            
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    # --- НАДЕТЬ / СНЯТЬ АКСЕССУАР ---
    elif call.data.startswith("equip_acc_"):
        try:
            idx = int(call.data.replace("equip_acc_", ""))
            if idx < len(user_data["accessories"]):
                item_name = user_data["accessories"][idx]
                if user_data["equipped"] == item_name:
                    user_data["equipped"] = ""
                    bot.answer_callback_query(call.id, f"Снято: {item_name}", show_alert=False)
                else:
                    user_data["equipped"] = item_name
                    bot.answer_callback_query(call.id, f"Надето: {item_name}", show_alert=False)
                save_user(chat_id, user_data)
                
                # Переоткрываем инвентарь, чтобы обновить кнопки
                call.data = "inventory_menu"
                callback_handler(call)
        except Exception as e:
            bot.answer_callback_query(call.id, "Ошибка при выборе предмета", show_alert=True)

    # --- ЗАПУСК ИГРЫ 21 ---
    elif call.data == "start_21":
        bot.answer_callback_query(call.id)
        if user_data["balance"] < 5:
            bot.answer_callback_query(call.id, "❌ Минимальная ставка для игры в 21 — 5 монет!", show_alert=True)
            return
        
        bet = 5.0
        deck = list(CARDS.keys()) * 4
        random.shuffle(deck)
        
        player_cards = [deck.pop(), deck.pop()]
        dealer_cards = [deck.pop(), deck.pop()]
        
        ACTIVE_GAMES_21[chat_id] = {
            "deck": deck,
            "player_cards": player_cards,
            "dealer_cards": dealer_cards,
            "bet": bet
        }
        
        p_score = calculate_score(player_cards)
        text = (
            "🃏 **Игра в 21 (Очко)**\n\n"
            f"📥 Ваши карты: {', '.join(player_cards)} (Очки: **{p_score}**)\n"
            f"🎴 Карта дилера: {dealer_cards[0]}, [скрыто]\n\n"
            f"Ставка: {bet} монет. Что делаем?"
        )
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("➕ Взять", callback_data="game21_hit"),
            InlineKeyboardButton("🛑 Хватит", callback_data="game21_stand")
        )
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "game21_hit":
        bot.answer_callback_query(call.id)
        if chat_id not in ACTIVE_GAMES_21:
            bot.answer_callback_query(call.id, "⚠️ Игра не найдена. Начните заново.", show_alert=True)
            return
            
        game = ACTIVE_GAMES_21[chat_id]
        card = game["deck"].pop()
        game["player_cards"].append(card)
        p_score = calculate_score(game["player_cards"])
        
        if p_score > 21:
            user_data["balance"] -= game["bet"]
            save_user(chat_id, user_data)
            text = (
                "💥 **Перебор! Вы проиграли.**\n\n"
                f"Ваши карты: {', '.join(game['player_cards'])} (Очки: **{p_score}**)\n"
                f"❌ Списано: {game['bet']} монет.\n"
                f"💰 Баланс: {round(user_data['balance'], 2)} монет"
            )
            del ACTIVE_GAMES_21[chat_id]
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=main_menu_markup(), parse_mode="Markdown")
        else:
            text = (
                "🃏 **Игра в 21 (Очко)**\n\n"
                f"📥 Ваши карты: {', '.join(game['player_cards'])} (Очки: **{p_score}**)\n"
                f"🎴 Карта дилера: {game['dealer_cards'][0]}, [скрыто]\n\n"
                "Что делаем дальше?"
            )
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("➕ Взять", callback_data="game21_hit"),
                InlineKeyboardButton("🛑 Хватит", callback_data="game21_stand")
            )
            bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "game21_stand":
        bot.answer_callback_query(call.id)
        if chat_id not in ACTIVE_GAMES_21:
            bot.answer_callback_query(call.id, "⚠️ Игра не найдена. Начните заново.", show_alert=True)
            return
            
        game = ACTIVE_GAMES_21[chat_id]
        p_score = calculate_score(game["player_cards"])
        d_score = calculate_score(game["dealer_cards"])
        
        while d_score < 17 and len(game["deck"]) > 0:
            game["dealer_cards"].append(game["deck"].pop())
            d_score = calculate_score(game["dealer_cards"])
            
        bet = game["bet"]
        result_text = ""
        
        if d_score > 21 or p_score > d_score:
            user_data["balance"] += bet
            result_text = f"🎉 **Победа!** Вы выиграли {bet} монет!"
        elif p_score == d_score:
            result_text = "🤝 **Ничья!** Ставка возвращена."
        else:
            user_data["balance"] -= bet
            result_text = f"😢 **Дилер победил.** Вы потеряли {bet} монет."
            
        save_user(chat_id, user_data)
        
        text = (
            f"{result_text}\n\n"
            f"👤 Ваши карты: {', '.join(game['player_cards'])} (Очки: **{p_score}**)\n"
            f"🤖 Карты дилера: {', '.join(game['dealer_cards'])} (Очки: **{d_score}**)\n\n"
            f"💰 Баланс: **{round(user_data['balance'], 2)} монет**"
        )
        del ACTIVE_GAMES_21[chat_id]
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=text, reply_markup=main_menu_markup(), parse_mode="Markdown")

if __name__ == "__main__":
    init_db()
    logging.info("Бот запущен. Инвентарь и игра в 21 работают стабильно.")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            logging.error(f"Ошибка polling: {e}")
            time.sleep(5)
