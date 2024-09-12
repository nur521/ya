import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import mysql.connector
from mysql.connector import errors

API_TOKEN = '7377740873:AAH7Wgia_s_kivchJgCT6uuOLfI-_Xpr1XI'
CHANNEL_ID = '-1002181122538'
BOT_NICKNAME = 'MineEarnCoin_bot'
TOTAL_SUPPLY = 100_000_000_000  # 100 миллиардов токенов

bot = telebot.TeleBot(API_TOKEN)

# Подключаемся к базе данных MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="n@1234mine@4321",
    database="tokens_db"
)
cursor = conn.cursor()

# Создаем таблицы, если они еще не созданы
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    tokens INT DEFAULT 0,
    referred_by BIGINT,
    referral_count INT DEFAULT 0,
    received_initial_tokens BOOLEAN DEFAULT 0,
    wallet_address VARCHAR(255)
)''')
conn.commit()

def create_markup(include_menu=False, include_balance=False):
    """Создаем клавиатуру с кнопками. Кнопка Menu добавляется только если include_menu=True, Balance — если include_balance=True."""
    markup = InlineKeyboardMarkup()
    subscribe_button = InlineKeyboardButton("Subscribe", url="https://t.me/nuriknik")
    
    if not include_menu:  # Включаем кнопку Check только до нажатия Menu
        check_button = InlineKeyboardButton("Check", callback_data="check")
        markup.add(subscribe_button, check_button)
    else:
        markup.add(subscribe_button)
    
    if include_balance:
        balance_button = InlineKeyboardButton("Balance", callback_data="balance")
        markup.add(balance_button)
    
    if include_menu:
        menu_button = InlineKeyboardButton("Menu", callback_data="menu")
        referral_button = InlineKeyboardButton("Referral Info", callback_data="referral_info")  # Одна кнопка для рефералов
        all_tokens_button = InlineKeyboardButton("All Tokens", callback_data="all_tokens")  # Кнопка All Tokens
        markup.add(menu_button, referral_button, all_tokens_button)
    
    return markup

# Функция для расчета оставшихся токенов
def get_remaining_tokens():
    cursor.execute("SELECT SUM(tokens) FROM users")
    used_tokens = cursor.fetchone()[0] or 0
    remaining_tokens = TOTAL_SUPPLY - used_tokens
    return remaining_tokens

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Проверяем, есть ли пользователь в базе данных, если нет - добавляем
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        referrer_id = message.text.split()[-1] if len(message.text.split()) > 1 else None
        remaining_tokens = get_remaining_tokens()
        
        # Проверка, что оставшихся токенов достаточно для нового пользователя
        if remaining_tokens >= 3000:
            try:
                cursor.execute("INSERT INTO users (user_id, username, tokens, referred_by, received_initial_tokens) VALUES (%s, %s, 0, %s, 0)", 
                            (user_id, username, referrer_id))
                conn.commit()
            except mysql.connector.Error as err:
                print(f"Ошибка: {err}")
                bot.send_message(message.chat.id, "Произошла ошибка при создании пользователя.")
                return

            # Обновляем количество рефералов у реферера и добавляем токены
            if referrer_id:
                cursor.execute("SELECT referral_count, tokens FROM users WHERE user_id = %s", (referrer_id,))
                referrer = cursor.fetchone()
                if referrer and remaining_tokens >= 50:
                    new_referral_count = referrer[0] + 1
                    new_tokens = referrer[1] + (2000 if new_referral_count == 5 else 50)  # 2000 токенов за 5 рефералов, 50 за остальных
                    cursor.execute("UPDATE users SET referral_count = %s, tokens = %s WHERE user_id = %s", 
                                (new_referral_count, new_tokens, referrer_id))
                    conn.commit()
        else:
            bot.send_message(message.chat.id, "К сожалению, все токены закончились.")
            return

    markup = create_markup()  # Только Subscribe и Check
    bot.send_message(message.chat.id, "Hi! Please subscribe to our channel and click /check to check, then, receive tokens.", reply_markup=markup)

# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    if call.data == "check":
        markup = create_markup(include_menu=True)  # После проверки добавляем Menu и убираем Check
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        
        if chat_member.status in ['member', 'administrator', 'creator']:
            cursor.execute("SELECT received_initial_tokens, tokens, referral_count FROM users WHERE user_id = %s", (user_id,))
            user_data = cursor.fetchone()
            received_initial_tokens = user_data[0]
            user_tokens = user_data[1]
            referral_count = user_data[2]
            remaining_tokens = get_remaining_tokens()
            
            if not received_initial_tokens:
                if remaining_tokens >= 3000:
                    cursor.execute("UPDATE users SET tokens = tokens + 3000, received_initial_tokens = 1 WHERE user_id = %s", (user_id,))
                    conn.commit()

                    web_app_url = f"https://nur521.github.io/xa/?username={call.from_user.username}&user_id={user_id}&balance={user_tokens + 3000}&remaining_tokens={remaining_tokens}&referrals={referral_count}"

                    web_app_markup = InlineKeyboardMarkup()
                    web_app_button = InlineKeyboardButton("Open Web App", url=web_app_url)
                    web_app_markup.add(web_app_button)

                    bot.send_message(call.message.chat.id, "Great! You are subscribed. Open the web app below:", reply_markup=web_app_markup)

                    bot.send_message(call.message.chat.id, "You earned 3000 MineCoins.\n\nUse the menu below:", reply_markup=markup)
                else:
                    bot.send_message(call.message.chat.id, "К сожалению, все токены закончились.")
            else:
                web_app_url = f"https://nur521.github.io/xa/?username={call.from_user.username}&user_id={user_id}&balance={user_tokens}&remaining_tokens={remaining_tokens}&referrals={referral_count}"

                web_app_markup = InlineKeyboardMarkup()
                web_app_button = InlineKeyboardButton("Open Web App", url=web_app_url)
                web_app_markup.add(web_app_button)
                bot.send_message(call.message.chat.id, "Great! You are subscribed. Open the web app below:", reply_markup=web_app_markup)
                bot.send_message(call.message.chat.id, "You have already received your 3000 tokens.\n\nUse the menu below:", reply_markup=markup)
                
        else:
            bot.send_message(call.message.chat.id, "You are not subscribed to the channel. Please subscribe and try again.\n\nUse the menu below:", reply_markup=markup)
    
    elif call.data == "balance":
        cursor.execute("SELECT tokens FROM users WHERE user_id = %s", (user_id,))
        tokens = cursor.fetchone()[0]
        markup = create_markup(include_menu=True, include_balance=True)
        bot.send_message(call.message.chat.id, f"You have {tokens} MineCoins.\n\nUse the menu below:", reply_markup=markup)
    
    elif call.data == "menu":
        markup = create_markup(include_menu=True)
        bot.send_message(call.message.chat.id, f"Hi {call.from_user.username}! Welcome to MineCoin.\n\nUse the menu below:", reply_markup=markup)

    elif call.data == "all_tokens":
        # Отправляем информацию о всех оставшихся токенах
        remaining_tokens = get_remaining_tokens()
        bot.send_message(call.message.chat.id, f"Осталось {remaining_tokens} токенов.\n\nUse the menu below:", reply_markup=create_markup(include_menu=True))

    elif call.data == "referral_info":
        # Показываем количество рефералов и реферальную ссылку пользователя
        cursor.execute("SELECT referral_count FROM users WHERE user_id = %s", (user_id,))
        referral_count = cursor.fetchone()[0]
        referral_link = f"https://t.me/{BOT_NICKNAME}?start={user_id}"
        bot.send_message(call.message.chat.id, f"You have {referral_count} referrals.\nYour referral link is: {referral_link}")

bot.polling()
