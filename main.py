import time
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice

TOKEN = "8631846961:AAGpjWYBTBugvefFkiWBSucihBEZBthlY2M"
bot = telebot.TeleBot(TOKEN)

users = {}

# Обычная недвижимость (за монеты) с уменьшенным доходом
HOUSES = {
    "house_1": {"name": "🏠 Гараж", "price": 100, "income": 0.2},
    "house_2": {"name": "🏢 Офис", "price": 600, "income": 1.2},
    "house_3": {"name": "🏭 Завод", "price": 2500, "income": 5.0},
    "house_4": {"name": "🏙️ Торговый центр", "price": 10000, "income": 18.0}
}

# Премиум недвижимость (за Звёзды XTR)
STAR_HOUSES = {
    "star_cafe": {"name": "☕ Частная кофейня", "price": 15, "income": 25.0},
    "star_1": {"name": "💎 IT-Корпорация", "price": 50, "income": 80.0},
    "star_2": {"name": "🚀 Космопорт", "price": 150, "income": 300.0}
}

# Инвестиции с медленной и честной окупаемостью (дробный доход)
INVESTMENTS = {
    "inv_1": {"name": "🌱 Крипто-ферма", "price": 30, "income": 0.1},
    "inv_2": {"name": "☕ Кофейный ларек", "price": 70, "income": 0.3},
    "inv_3": {"name": "⛽ Автомойка", "price": 350, "income": 1.0},
    "inv_4": {"name": "🚢 Логистическая компания", "price": 1500, "income": 4.5}
}

def get_user(chat_id):
    if chat_id not in users:
        users[chat_id] = {"balance": 20.0, "properties": [], "investments": []}
    return users[chat_id]

# Фоновый поток для плавно капающего дохода каждую секунду
def income_loop():
    while True:
        time.sleep(1)
        for chat_id, user in users.items():
            total_income = 0.0
            for p in user["properties"]:
                for item in {**HOUSES, **STAR_HOUSES}.values():
                    if item["name"] == p:
                        total_income += item["income"]
            for inv in user["investments"]:
                for item in INVESTMENTS.values():
                    if item["name"] == inv:
                        total_income += item["income"]
            
            if total_income > 0:
                user["balance"] += total_income

# Запуск фонового потока
threading.Thread(target=income_loop, daemon=True).start()

def main_menu_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("💰 Баланс", callback_data="balance"), InlineKeyboardButton("📊 Доход", callback_data="income_info"))
    markup.row(InlineKeyboardButton("🏢 Магазин", callback_data="shop"), InlineKeyboardButton("📈 Инвестиции", callback_data="invest_menu"))
    markup.row(InlineKeyboardButton("📂 Имущество", callback_data="my_props"))
    return markup

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(message.chat.id, "🌆 Добро пожаловать в симулятор магната!\nРазвивай бизнес, инвестируй с умом и зарабатывай.", reply_markup=main_menu_markup())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user = get_user(chat_id)
    
    if call.data == "balance":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"💰 Твой баланс: {round(user['balance'], 2)} монет", reply_markup=main_menu_markup())
        
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
        bot.send_message(chat_id, f"📊 Твой общий доход: {round(total_income, 2)} монет в секунду", reply_markup=main_menu_markup())
        
    elif call.data == "shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in HOUSES.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет (+{item['income']}/с)", callback_data=f"buy_coin_{key}"))
        for key, item in STAR_HOUSES.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — ⭐ {item['price']} Звёзд (+{item['income']}/с)", callback_data=f"buy_star_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.send_message(chat_id, "🏪 Магазин недвижимости:", reply_markup=markup)
        
    elif call.data == "invest_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in INVESTMENTS.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет (+{item['income']}/с)", callback_data=f"buy_inv_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.send_message(chat_id, "📈 Инвестиционные фонды и проекты:", reply_markup=markup)
        
    elif call.data.startswith("buy_inv_"):
        inv_key = call.data.replace("buy_inv_", "")
        item = INVESTMENTS[inv_key]
        if user["balance"] >= item["price"]:
            user["balance"] -= item["price"]
            user["investments"].append(item["name"])
            bot.answer_callback_query(call.id, "Успешно куплено!")
            bot.send_message(chat_id, f"✅ Ты успешно профинансировал «{item['name']}»!", reply_markup=main_menu_markup())
        else:
            bot.answer_callback_query(call.id, "Недостаточно монет!", show_alert=True)
            
    elif call.data.startswith("buy_coin_"):
        house_key = call.data.replace("buy_coin_", "")
        item = HOUSES[house_key]
        if user["balance"] >= item["price"]:
            user["balance"] -= item["price"]
            user["properties"].append(item["name"])
            bot.answer_callback_query(call.id, "Успешно куплено!")
            bot.send_message(chat_id, f"🎉 Поздравляем с покупкой: {item['name']}!", reply_markup=main_menu_markup())
        else:
            bot.answer_callback_query(call.id, "Недостаточно монет!", show_alert=True)
            
    elif call.data.startswith("buy_star_"):
        house_key = call.data.replace("buy_star_", "")
        item = STAR_HOUSES[house_key]
        bot.answer_callback_query(call.id)
        prices = [LabeledPrice(label=item['name'], amount=item['price'])]
        bot.send_invoice(
            chat_id=chat_id,
            title=item['name'],
            description=f"Купить премиум-актив '{item['name']}' за Телеграм Звёзды",
            invoice_payload=f"buy_prop_{house_key}",
            provider_token="",
            currency="XTR",
            prices=prices
        )
            
    elif call.data == "my_props":
        bot.answer_callback_query(call.id)
        props = ", ".join(user["properties"]) if user["properties"] else "нет"
        invs = ", ".join(user["investments"]) if user["investments"] else "нет"
        text = f"📂 Твое имущество:\n\n🏢 Недвижимость:\n{props}\n\n📈 Инвестиции:\n{invs}"
        bot.send_message(chat_id, text, reply_markup=main_menu_markup())
            
    elif call.data == "menu":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "Главное меню:", reply_markup=main_menu_markup())

@bot.message_handler(content_types=["successful_payment"])
def got_payment(message):
    payment = message.successful_payment
    chat_id = message.chat.id
    user = get_user(chat_id)
    if payment.invoice_payload.startswith("buy_prop_"):
        house_key = payment.invoice_payload.replace("buy_prop_", "")
        item = STAR_HOUSES[house_key]
        user["properties"].append(item["name"])
        bot.send_message(chat_id, f"⭐ Оплата прошла успешно! Премиум-актив «{item['name']}» добавлен в твоё имущество!")

if __name__ == "__main__":
    print("Бот с обновленной экономикой запущен...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
