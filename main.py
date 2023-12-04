import os

# client = OpenAI(api_key="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",)
#
#
# completion = client.chat.completions.create(
#   model="gpt-3.5-turbo",
#   messages=[
#     {"role": "system", "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."},
#     {"role": "user", "content": "Compose a poem that explains the concept of recursion in programming."}
#   ]
# )
#
# print(completion.choices[0].message)
import telebot
import sqlite3
from openai import OpenAI

TOKEN = "6223135936:AAHj7gpcKVi36TG4bIZ4S971qzUlQNtJxeM"

bot = telebot.TeleBot(TOKEN)

keyboard_settings = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True).add("Type network").row(
    "Description of the defendant")

users_cache = dict()
list_with_type_network = ["gpt-3.5-turbo"]
keyboard_network = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
for i in list_with_type_network:
    keyboard_network.row(i)


def update_user_cache(message):
    global users_cache
    if not (message.from_user.id in users_cache):
        con = sqlite3.connect("users")

        cur = con.cursor()

        result = cur.execute(f"""SELECT SECRET_KEY FROM USERS
                            WHERE TELEGRAM_ID = {message.from_user.id}""").fetchall()

        if result:
            users_cache[message.from_user.id] = {"KEY": "", "settings": {
                "model": "gpt-3.5-turbo",
                "role": "You are a poetic assistant, skilled in explaining complex "
                        "programming concepts with creative flair."
            }}
            users_cache[message.from_user.id]["KEY"] = result[0]
        else:
            con.close()
            return False
        con.close()
    return True


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.from_user.id, "To authorize, write /authorization")


@bot.message_handler(commands=['authorization'])
def authorization(message):
    bot.send_message(message.from_user.id, "send you SECRET_KEY")
    bot.register_next_step_handler(message, add_secret_key)


def add_secret_key(message: telebot.types.Message):
    con = sqlite3.connect("users")
    cur = con.cursor()
    cur.execute(f"""INSERT INTO USERS(TELEGRAM_ID,SECRET_KEY) 
                        VALUES({message.from_user.id},'{message.text}')""")
    con.commit()
    con.close()
    update_user_cache(message)

    bot.send_message(message.from_user.id, "Authorization was successful")


@bot.message_handler(commands=['settings'])
def settings(message):
    if update_user_cache(message):
        bot.send_message(message.from_user.id, "Choose", reply_markup=keyboard_settings)
        bot.register_next_step_handler(message, choose_settings)
    else:
        bot.send_message(message.from_user.id, "To authorize, write /authorization")


def choose_settings(message):
    if message.text == "Type network":
        bot.send_message(message.from_user.id, "Choose", reply_markup=keyboard_network)
        bot.register_next_step_handler(message, set_network)
    else:
        bot.send_message(message.from_user.id, "Send me description")
        bot.register_next_step_handler(message, set_description)


def set_network(message):
    global users_cache
    if message.text in list_with_type_network:
        users_cache[message.from_user.id]["settings"]["model"] = message.text
        bot.send_message(message.from_user.id, "OK")
    else:
        bot.send_message(message.from_user.id, "I don't know this network")


def set_description(message):
    global users_cache
    users_cache[message.from_user.id]["settings"]["role"] = message.text
    bot.send_message(message.from_user.id, "OK")


@bot.message_handler(content_types=["text"])
def text_handler(message):
    if not update_user_cache(message):
        bot.send_message(message.from_user.id, "To authorize, write /authorization")
        return
    client = OpenAI(api_key=users_cache[message.from_user.id]["KEY"][0])

    completion = client.chat.completions.create(
        model=users_cache[message.from_user.id]["settings"]["model"],
        messages=[
            {"role": "system", "content": users_cache[message.from_user.id]["settings"]["role"]},
            {"role": "user", "content": message.text}
        ]
    )
    bot.send_message(message.from_user.id, str(completion.choices[0].message))


bot.polling()
