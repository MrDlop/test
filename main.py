import datetime

import telebot
from openai import OpenAI
from telebot import types

import config
from data.messages import Message
from script import lang, bot_answer
from data import db_session

from data.companies import Company
from data.companies_users import CompanyUser
from data.prompts import Prompt
from data.users import User
from sqlalchemy.sql.expression import func

db_session.global_init("db/db.db")

TOKEN = config.TOKEN

bot = telebot.TeleBot(TOKEN)
client = OpenAI(api_key=config.API_KEY)

type_network = "gpt-3.5-turbo"

keyboard_confirm = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True).row(bot_answer[lang]['confirm'])
keyboard_login = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True).row(bot_answer[lang]['login'])


def main_menu(message):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not (user is None):
        markup = types.InlineKeyboardMarkup()
        out = types.InlineKeyboardButton(bot_answer[lang]['logout'], callback_data="logout")
        markup.row(out)
        setting = types.InlineKeyboardButton(bot_answer[lang]['settings'], callback_data="settings")
        markup.row(setting)
        if user.company_id == 0:
            add = types.InlineKeyboardButton(bot_answer[lang]['add'], callback_data="add")
            markup.row(add)
            delete = types.InlineKeyboardButton(bot_answer[lang]['del'], callback_data="del")
            markup.row(delete)
            upd_time = types.InlineKeyboardButton(bot_answer[lang]['upd_time'], callback_data="upd_time")
            markup.row(upd_time)
            upd_lim = types.InlineKeyboardButton(bot_answer[lang]['upd_lim'], callback_data="upd_lim")
            markup.row(upd_lim)
            add_prompt = types.InlineKeyboardButton(bot_answer[lang]['add_prompt'], callback_data="add_prompt")
            markup.row(add_prompt)
        bot.send_message(message.from_user.id, bot_answer[lang]["start_ok"], reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()
        auth = types.InlineKeyboardButton(bot_answer[lang]['login'], callback_data="login")
        markup.row(auth)
        bot.send_message(message.from_user.id, bot_answer[lang]["not_authorization"], reply_markup=markup)


@bot.message_handler(commands=['start'])
def start(message: telebot.types.Message) -> None:
    main_menu(message)


@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data == "login":
        bot.send_message(callback.from_user.id, bot_answer[lang]["authorization_name"])
        bot.register_next_step_handler(callback.message, authorization_name)
    elif callback.data == "logout":
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not (user is None):
            db_sess.delete(user)
            db_sess.commit()
        markup = types.InlineKeyboardMarkup()
        auth = types.InlineKeyboardButton(bot_answer[lang]['login'], callback_data="login")
        markup.row(auth)
        bot.send_message(callback.from_user.id, bot_answer[lang]["not_authorization"], reply_markup=markup)
    elif callback.data == "settings":
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.telegram_id == callback.from_user.id).first()

        if user is None:
            markup = types.InlineKeyboardMarkup()
            auth = types.InlineKeyboardButton(bot_answer[lang]['login'], callback_data="login")
            markup.row(auth)
            bot.send_message(callback.from_user.id, bot_answer[lang]["not_authorization"], reply_markup=markup)
            return
        prompts = db_sess.query(Prompt).all()
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i in prompts:
            keyboard.row(i.description)
        bot.send_message(callback.from_user.id, bot_answer[lang]["prompt"], reply_markup=keyboard)
        bot.register_next_step_handler(callback.message, prompt)
    # Administration
    else:
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if user is None or user.company_id != 0:
            main_menu(callback.message)
            return
        if callback.data == "del":
            bot.send_message(callback.from_user.id, bot_answer[lang]["choose_company"])
            bot.register_next_step_handler(callback.message, admin_delete_company_confirm)
        elif callback.data == "add":
            bot.send_message(callback.from_user.id, bot_answer[lang]["input_name_company"])
            bot.register_next_step_handler(callback.message, admin_add_company_password)
        elif callback.data == "upd_time":
            bot.send_message(callback.from_user.id, bot_answer[lang]["input_name_company"])
            bot.register_next_step_handler(callback.message, admin_update_date_date)
        elif callback.data == "upd_lim":
            bot.send_message(callback.from_user.id, bot_answer[lang]["input_name_company"])
            bot.register_next_step_handler(callback.message, admin_update_limit_user_limit)
        elif callback.data == "add_prompt":
            bot.send_message(callback.from_user.id, bot_answer[lang]["input_prompt"])
            bot.register_next_step_handler(callback.message, admin_add_prompt_description)


def authorization_name(message: telebot.types.Message) -> None:
    bot.send_message(message.from_user.id, bot_answer[lang]["authorization_password"])
    bot.register_next_step_handler(message, authorization_password, message.text)


def authorization_password(message: telebot.types.Message, company_name: str) -> None:
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id
    db_sess = db_session.create_session()
    company = db_sess.query(Company).filter(Company.company_name == company_name).first()
    if not (company is None) and company.check_password(message.text):
        user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
        if user is None:
            user_count = len(db_sess.query(CompanyUser).filter(CompanyUser.company_id ==
                                                               company.company_id).all())
            if user_count < company.max_num_users:
                user_company = CompanyUser()
                user = User()
                max_id = db_sess.query(func.max(CompanyUser.ID)).first()[0]
                if max_id is None:
                    max_id = -1
                user_company.ID = max_id + 1
                user.telegram_id = user_company.telegram_id = message.from_user.id
                user.company_id = user_company.company_id = company.company_id
            else:
                bot.delete_message(message.from_user.id, msg_temp)
                bot.send_message(message.from_user.id, bot_answer[lang]["authorization_fail_1"])
                main_menu(message)
                return
            db_sess.add(user)
            db_sess.add(user_company)
        else:
            user.company_id = company.company_id
        db_sess.commit()
        bot.delete_message(message.from_user.id, msg_temp)
        main_menu(message)
    else:
        msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id
        bot.send_message(message.from_user.id, bot_answer[lang]["authorization_fail"])
        main_menu(message)


def prompt(message: telebot.types.Message) -> None:
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    prompt_ = db_sess.query(Prompt).filter(Prompt.description == message.text).first()
    if prompt_ is None:
        bot.send_message(message.from_user.id, bot_answer[lang]["incorrect_prompt"])
    else:
        user.prompt = prompt_.prompt
    bot.delete_message(message.from_user.id, msg_temp)
    main_menu(message)


def admin_delete_company_confirm(message: telebot.types.Message) -> None:
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id
    db_sess = db_session.create_session()
    company = db_sess.query(Company).filter(Company.company_name == message.text).first()
    if company is None:
        bot.delete_message(message.from_user.id, msg_temp)
        bot.send_message(message.from_user.id, bot_answer[lang]["unreal_company"])
        return
    bot.delete_message(message.from_user.id, msg_temp)
    bot.send_message(message.from_user.id, bot_answer[lang]["confirm"], reply_markup=keyboard_confirm)
    bot.register_next_step_handler(message, admin_delete_company, (company.company_name,))


def admin_delete_company(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company
    :return:
    """
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id
    if message.text == bot_answer[lang]["confirm"]:
        db_sess = db_session.create_session()
        company = db_sess.query(Company).filter(Company.company_name == data[0]).first()
        users = db_sess.query(User).filter(User.company_id == company.company_id).all()
        for user in users:
            db_sess.delete(user)
        users = db_sess.query(CompanyUser).filter(CompanyUser.company_id == company.company_id).all()
        for user in users:
            db_sess.delete(user)
        db_sess.delete(company)
        db_sess.commit()

    bot.delete_message(message.from_user.id, msg_temp)
    bot.send_message(message.from_user.id, bot_answer[lang]["ok"])
    main_menu(message)


def admin_add_company_password(message: telebot.types.Message) -> None:
    bot.send_message(message.from_user.id, bot_answer[lang]["input_password"])
    bot.register_next_step_handler(message, admin_add_company_count, (message.text,))


def admin_add_company_count(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company
    :return:
    """
    bot.send_message(message.from_user.id, bot_answer[lang]["input_num_of_user"])
    bot.register_next_step_handler(message, admin_add_company_date, (*data, message.text))


def admin_add_company_date(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company, password
    :return:
    """
    bot.send_message(message.from_user.id, bot_answer[lang]["input_time"])
    bot.register_next_step_handler(message, admin_add_company_confirm, (*data, message.text))


def admin_add_company_confirm(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company, password, number of users
    :return:
    """
    bot.send_message(message.from_user.id, f"""
                     {data[0]}
                     {data[1]}
                     {data[2]}
                     {message.text}""",
                     reply_markup=keyboard_confirm)
    bot.register_next_step_handler(message, admin_add_company, (*data, message.text))


def admin_add_company(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company, password, max numbers of users, date
    """
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id
    if message.text == bot_answer[lang]["confirm"]:
        try:
            db_sess = db_session.create_session()
            company = db_sess.query(Company).filter(Company.company_name == data[0]).first()
            if company is None:
                max_id = db_sess.query(func.max(Company.company_id)).first()
                company = Company(
                    company_id=max_id[0] + 1,
                    company_name=data[0],
                    max_num_users=data[2],
                    time=data[3]
                )
                company.set_password(data[1])
                db_sess.add(company)
                db_sess.commit()
            else:
                raise ValueError
        except ValueError:
            bot.delete_message(message.from_user.id, msg_temp)
            bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
            main_menu(message)
            return

    bot.delete_message(message.from_user.id, msg_temp)
    bot.send_message(message.from_user.id, bot_answer[lang]["ok"])
    main_menu(message)


def admin_update_limit_user_limit(message: telebot.types.Message) -> None:
    bot.send_message(message.from_user.id, bot_answer[lang]["input_num_of_user"])
    bot.register_next_step_handler(message, admin_update_limit_user_confirm, (message.text,))


def admin_update_limit_user_confirm(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company
    :return:
    """
    bot.send_message(message.from_user.id, f"""
                     {data[0]}
                     {message.text}
                     {message.text}""",
                     reply_markup=keyboard_confirm)
    bot.register_next_step_handler(message, admin_update_limit_user, (*data, message.text))


def admin_update_limit_user(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company, max numbers of users
    """
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id
    if message.text == bot_answer[lang]["confirm"]:
        try:
            db_sess = db_session.create_session()
            company = db_sess.query(Company).filter(Company.company_name == data[0]).first()
            if company is None:
                bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
                main_menu(message)
                return
            company[0].max_num_users = data[1]
            db_sess.commit()
        except ValueError:
            bot.delete_message(message.from_user.id, msg_temp)
            bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
            main_menu(message)
            return

    bot.delete_message(message.from_user.id, msg_temp)
    bot.send_message(message.from_user.id, bot_answer[lang]["ok"])
    main_menu(message)


def admin_update_date_date(message: telebot.types.Message) -> None:
    bot.send_message(message.from_user.id, bot_answer[lang]["input_time"])
    bot.register_next_step_handler(message, admin_update_date_confirm, (message.text,))


def admin_update_date_confirm(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company
    :return:
    """
    bot.send_message(message.from_user.id, f"""
                     {data[0]}
                     {message.text}
                     {message.text}""",
                     reply_markup=keyboard_confirm)
    bot.register_next_step_handler(message, admin_update_date, (*data, message.text))


def admin_update_date(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company, date
    """
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id

    if message.text == bot_answer[lang]["confirm"]:
        try:
            db_sess = db_session.create_session()
            company = db_sess.query(Company).filter(Company.company_name == data[0]).first()
            if company is None:
                bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
                main_menu(message)
                return
            company[0].set_time(time=data[1])
            db_sess.commit()
        except ValueError:
            bot.delete_message(message.from_user.id, msg_temp)
            bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
            main_menu(message)
            return

    bot.delete_message(message.from_user.id, msg_temp)
    bot.send_message(message.from_user.id, bot_answer[lang]["ok"])
    main_menu(message)


def admin_add_prompt_description(message: telebot.types.Message) -> None:
    bot.send_message(message.from_user.id, bot_answer[lang]["input_description"])
    bot.register_next_step_handler(message, admin_add_prompt_confirm, message.text)


def admin_add_prompt_confirm(message: telebot.types.Message, prompt_text: str) -> None:
    bot.send_message(message.from_user.id, bot_answer[lang]["confirm"], reply_markup=keyboard_confirm)
    bot.register_next_step_handler(message, admin_add_prompt, (prompt_text, message.text))


def admin_add_prompt(message: telebot.types.Message, prompt_all: tuple) -> None:
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id

    if message.text == bot_answer[lang]["confirm"]:
        try:
            db_sess = db_session.create_session()
            prompt_ = Prompt()
            prompt_.prompt = prompt_all[0]
            prompt_.description = prompt_all[1]
            db_sess.add(prompt_)
            db_sess.commit()
        except ValueError:
            bot.delete_message(message.from_user.id, msg_temp)
            bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
            main_menu(message)
            return

    bot.delete_message(message.from_user.id, msg_temp)
    bot.send_message(message.from_user.id, bot_answer[lang]["ok"])
    main_menu(message)


@bot.message_handler(content_types=["text"])
def text_handler(message: telebot.types.Message) -> None:
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()

    if user is None:
        bot.delete_message(message.from_user.id, msg_temp)
        main_menu(message)
        return
    if user.company.time <= datetime.datetime.now():
        bot.delete_message(message.from_user.id, msg_temp)
        bot.send_message(message.from_user.id, bot_answer[lang]["end_time"])
        main_menu(message)
        return
    messages = [
        {"role": "system", "content": "You are a helpful assistant." + user.prompt}
    ]
    mess = db_sess.query(Message).filter(Message.company_id == user.company_id
                                         and Message.telegram_id == user.telegram_id).all()
    if not(mess is None):
        for msg in mess:
            messages.append(
                {"role": "user",
                 "content": msg.request}
            )
            messages.append(
                {"role": "assistant",
                 "content": msg.responce}
            )
    messages.append(
        {"role": "user", "content": message.text})
    completion = client.chat.completions.create(
        model=type_network,
        messages=messages
    )
    new_mess = Message()
    new_mess.telegram_id = user.telegram_id
    new_mess.company_id = user.company_id
    new_mess.request = message.text
    new_mess.response = str(completion.choices[0].message.content)
    db_sess.add(new_mess)
    db_sess.commit()

    bot.delete_message(message.from_user.id, msg_temp)
    bot.send_message(message.from_user.id, str(completion.choices[0].message.content))


bot.polling()
