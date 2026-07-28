import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice

TOKEN = "8631846961:AAGpjWYBTBugvefFkiWBSucihBEZBthlY2M"
bot = telebot.TeleBot(TOKEN)

users = {}

HOUSES = {
    "house_1": {"name": "🏠 Гараж", "price": 100, "income": 5},
    "house_2": {"name": "🏢 Офис", "price": 500, "income": 30}
}

STAR_HOUSES = {
    "star_1": {"name": "💎 IT-Корпорация", "price": 50, "income": 150}
}

INVESTMENTS = {
    "inv_1": {"name": "🌱 Крипто-ферма", "price": 5, "income": 2},
    "inv_2": {"name": "☕ Кофейный ларек", "price": 8, "income": 4}
}

def get_user(chat_id):
    if chat_id not in users:
        users[chat_id] = {"balance": 10, "properties": [], "investments": []}
    return users[chat_id]

def main_menu_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("💰 Баланс", callback_data="balance"), InlineKeyboardButton("📊 Доход", callback_data="income_info"))
    markup.row(InlineKeyboardButton("🏢 Магазин", callback_data="shop"), InlineKeyboardButton("📈 Инвестиции", callback_data="invest_menu"))
    markup.row(InlineKeyboardButton("📂 Имущество", callback_data="my_props"))
    return markup

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(message.chat.id, "Привет! Симулятор бизнесов и инвестиций.", reply_markup=main_menu_markup())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    user = get_user(chat_id)
    
    if call.data == "balance":
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"💰 Твой баланс: {user['balance']} монет", reply_markup=main_menu_markup())
        
    elif call.data == "income_info":
        bot.answer_callback_query(call.id)
        total_income = 0
        for p in user["properties"]:
            for item in {**HOUSES, **STAR_HOUSES}.values():
                if item["name"] == p:
                    total_income += item["income"]
        for inv in user["investments"]:
            for item in INVESTMENTS.values():
                if item["name"] == inv:
                    total_income += item["income"]
        bot.send_message(chat_id, f"📊 Твой общий доход: {total_income} монет в секунду", reply_markup=main_menu_markup())
        
    elif call.data == "shop":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in HOUSES.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет (доход: {item['income']}/с)", callback_data=f"buy_coin_{key}"))
        for key, item in STAR_HOUSES.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — ⭐ {item['price']} Звёзд (доход: {item['income']}/с)", callback_data=f"buy_star_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.send_message(chat_id, "🏪 Магазин недвижимости:", reply_markup=markup)
        
    elif call.data == "invest_menu":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        for key, item in INVESTMENTS.items():
            markup.row(InlineKeyboardButton(f"{item['name']} — {item['price']} монет (доход: {item['income']}/с)", callback_data=f"buy_inv_{key}"))
        markup.row(InlineKeyboardButton("🔙 Главное меню", callback_data="menu"))
        bot.send_message(chat_id, "📈 Дешевые инвестиции:", reply_markup=markup)
        
    elif call.data.startswith("buy_inv_"):
        inv_key = call.data.replace("buy_inv_", "")
        item = INVESTMENTS[inv_key]
        if user["balance"] >= item["price"]:
            user["balance"] -= item["price"]
            user["investments"].append(item["name"])
            bot.answer_callback_query(call.id, "Куплено!")
            bot.send_message(chat_id, f"✅ Ты купил «{item['name']}»!", reply_markup=main_menu_markup())
        else:
            bot.answer_callback_query(call.id, "Недостаточно монет!", show_alert=True)
            
    elif call.data.startswith("buy_coin_"):
        house_key = call.data.replace("buy_coin_", "")
        item = HOUSES[house_key]
        if user["balance"] >= item["price"]:
            user["balance"] -= item["price"]
            user["properties"].append(item["name"])
            bot.answer_callback_query(call.id, "Успешно куплено!")
            bot.send_message(chat_id, f"🎉 Куплено: {item['name']}!", reply_markup=main_menu_markup())
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
            description=f"Купить {item['name']} за Звёзды",
            invoice_payload=f"buy_prop_{house_key}",
            provider_token="",
            currency="XTR",
            prices=prices
        )
            
    elif call.data == "my_props":
        bot.answer_callback_query(call.id)
        props = ", ".join(user["properties"]) if user["properties"] else "нет"
        invs = ", ".join(user["investments"]) if user["investments"] else "нет"
        text = f"📂 Твое имущество:\n🏢 Недвижимость: {props}\n📈 Инвестиции: {invs}"
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
        bot.send_message(chat_id, f"🎉 Успешно! «{item['name']}» добавлена!")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
