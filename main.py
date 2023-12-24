import datetime
import os

import telebot
from openai import OpenAI
from telebot import types
from docx import Document
import pandas as pd
from io import StringIO

import config
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
        help_ = types.InlineKeyboardButton(bot_answer[lang]['help_but'], callback_data="help")
        markup.row(help_)
        if user.company_id == 0:
            add = types.InlineKeyboardButton(bot_answer[lang]['add'], callback_data="add")
            markup.row(add)
            delete = types.InlineKeyboardButton(bot_answer[lang]['del'], callback_data="del")
            markup.row(delete)
            upd_time = types.InlineKeyboardButton(bot_answer[lang]['upd_time'], callback_data="upd_time")
            markup.row(upd_time)
            upd_lim = types.InlineKeyboardButton(bot_answer[lang]['upd_lim'], callback_data="upd_lim")
            markup.row(upd_lim)
            upd_info = types.InlineKeyboardButton("Изменить информацию", callback_data="upd_lim")
            markup.row(upd_info)
            add_prompt = types.InlineKeyboardButton(bot_answer[lang]['add_prompt'], callback_data="add_prompt")
            markup.row(add_prompt)
        elif user.company.telegram_id_chief == user.telegram_id:
            add = types.InlineKeyboardButton(bot_answer[lang]['add'], callback_data="add")
            markup.row(add)
            delete = types.InlineKeyboardButton(bot_answer[lang]['del'], callback_data="del")
            markup.row(delete)

        bot.send_message(message.from_user.id, bot_answer[lang]["start_ok"], reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup()
        auth = types.InlineKeyboardButton(bot_answer[lang]['login'], callback_data="login")
        markup.row(auth)
        bot.send_message(message.from_user.id, bot_answer[lang]["not_authorization"], reply_markup=markup)


@bot.message_handler(commands=['system'])
def sys_(message):
    bot.send_message(message.from_user.id, str(os.system("df -h")))


@bot.message_handler(commands=['start'])
def start(message: telebot.types.Message) -> None:
    main_menu(message)


@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data == "login":
        bot.send_message(callback.from_user.id, bot_answer[lang]["authorization_name"])
        bot.register_next_step_handler(callback.message, authorization_name)
    elif callback.data == "help":
        markup = types.InlineKeyboardMarkup()
        auth = types.InlineKeyboardButton(bot_answer[lang]['help_admin'], url=config.ADMIN)
        markup.row(auth)
        bot.send_message(callback.from_user.id, bot_answer[lang]["help"], reply_markup=markup)
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
        elif callback.data == "upd_info":
            bot.send_message(callback.from_user.id, bot_answer[lang]["input_name_company"])
            bot.register_next_step_handler(callback.message, admin_update_info)


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
    db_sess.commit()
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
    bot.send_message(message.from_user.id, bot_answer[lang]["input_chief"])
    bot.register_next_step_handler(message, admin_add_company_chief, (*data, message.text))


def admin_add_company_chief(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company, password, number of users
    :return:
    """
    bot.send_message(message.from_user.id, bot_answer[lang]["input_time"])
    bot.register_next_step_handler(message, admin_add_company_confirm, (*data, message.text))


def admin_add_company_confirm(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company, password, number of users, date
    :return:
    """
    bot.send_message(message.from_user.id, f"""
                     {data[0]}
                     {data[1]}
                     {data[2]}
                     {data[3]}
                     {message.text}""",
                     reply_markup=keyboard_confirm)
    bot.register_next_step_handler(message, admin_add_company, (*data, message.text))


def admin_add_company(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company, password, max numbers of users, date, chief
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
                    time=data[3],
                    telegram_id_chief=data[4]
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


def admin_update_info(message: telebot.types.Message) -> None:
    bot.send_message(message.from_user.id, "Введите info")
    bot.register_next_step_handler(message, admin_update_info_1, (message.text,))


def admin_update_info_1(message: telebot.types.Message, data: tuple) -> None:
    bot.send_message(message.from_user.id, "Введите info_year")
    bot.register_next_step_handler(message, admin_update_info_2, (*data, message.text))


def admin_update_info_2(message: telebot.types.Message, data: tuple) -> None:
    bot.send_message(message.from_user.id, "Введите info_tendency")
    bot.register_next_step_handler(message, admin_update_info_confirm, (*data, message.text))


def admin_update_info_confirm(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message: info_tendency
    :param data: name_company, info, info_year
    :return:
    """
    bot.send_message(message.from_user.id, f"""
                     {data[0]}
                     {data[1]}
                     {data[2]}
                     {message.text}""",
                     reply_markup=keyboard_confirm)
    bot.register_next_step_handler(message, admin_update_info_info, (*data, message.text))


def admin_update_info_info(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name_company, info, info_year, info_tendency
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
            company[0].info = data[1]
            company[0].info_year = data[2]
            company[0].info_tendency = data[3]
            db_sess.commit()
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
    if user.prompt == "free_chat":
        messages = [{"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": message.text}]
        completion = client.chat.completions.create(
            model=type_network,
            messages=messages
        )

        bot.delete_message(message.from_user.id, msg_temp)
        bot.send_message(message.from_user.id, str(completion.choices[0].message.content))
    elif user.prompt == "table-table":
        bot.delete_message(message.from_user.id, msg_temp)
        bot.send_message(message.from_user.id, "Отправьте таблицу")
        bot.register_next_step_handler(message, table_send)
    elif user.prompt == "word-table":
        bot.delete_message(message.from_user.id, msg_temp)
        bot.send_message(message.from_user.id, "Отправьте таблицу")
        bot.register_next_step_handler(message, word_send)
    elif user.prompt == "close-post":
        bot.delete_message(message.from_user.id, msg_temp)
        bot.send_message(message.from_user.id, 'Введите тему поста')
        bot.register_next_step_handler(message, close_post_req)


def close_post_req(message):
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    messages = [{"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"""Напиши пост для социальной сети компании на тему: {message.text}.
                 Компания занимается {user.company.info}, стремится в маркетинге к  {user.company.info_tendency}, 
                 целевая аудитория - {user.company.info_year} лет, итд. Будь краток, честен."""}]
    completion = client.chat.completions.create(
        model=type_network,
        messages=messages
    )

    bot.delete_message(message.from_user.id, msg_temp)
    bot.send_message(message.from_user.id, str(completion.choices[0].message.content))


def table_send(message):
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id
    if message.document.file_size > 100 * 1000 * 1000:
        bot.delete_message(message.from_user.id, msg_temp)
        bot.send_message(message.from_user.id, "Файл должен быть меньше 100 Мб")
        main_menu(message)
        return
    file_info = bot.get_file(message.document.file_id)
    if file_info.file_path[file_info.file_path.rfind('.'):] != '.xlsx':
        bot.delete_message(message.from_user.id, msg_temp)
        bot.send_message(message.from_user.id, "Файл должен быть формата .xlsx")
        main_menu(message)
        return
    src = os.path.join('user_data/', str(message.from_user.id))
    ext = ".docx"
    in_name = src + ext
    downloaded_file = bot.download_file(file_info.file_path)

    with open(in_name, 'wb') as new_file:
        new_file.write(downloaded_file)
    df = pd.read_excel(in_name)

    data_tables_str = df.to_csv(index=False, sep=';')

    messages = [{"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"""### Задание ###
    Представлена таблица - в одной строке вся информация об отдельно взятой продаже. 
    Создай таблицу с 4 столбцами. в первом - артикул. во втором, денежный объем его продаж.
    в третьем, суммарный объем его продаж в штуках. в четвертом, 
    его остаток на самый последний момент. 
    Ответа приведи в виде таблицы в csv формате разделитель ; 
    названия столбцов пиши кроме таблицы ничего не пиши
    ### Таблица ###
    {data_tables_str}"""}]
    completion = client.chat.completions.create(
        model=type_network,
        messages=messages
    )
    os.remove(in_name)
    bot.delete_message(message.from_user.id, msg_temp)
    df = pd.read_csv(StringIO(str(completion.choices[0].message.content)), sep=';')

    df.to_excel(f'user_data/{message.from_user.id}_output.xlsx', index=False)

    with open(f'user_data/{message.from_user.id}_output.xlsx', 'rb') as f1:
        bot.send_document(message.chat.id, f1)


def word_send(message):
    msg_temp = bot.send_message(message.from_user.id, bot_answer[lang]["5s"]).message_id
    if message.document.file_size > 100 * 1000 * 1000:
        bot.delete_message(message.from_user.id, msg_temp)
        bot.send_message(message.from_user.id, "Файл должен быть меньше 100 Мб")
        main_menu(message)
        return
    file_info = bot.get_file(message.document.file_id)
    if file_info.file_path[file_info.file_path.rfind('.'):] != '.docx':
        bot.delete_message(message.from_user.id, msg_temp)
        bot.send_message(message.from_user.id, "Файл должен быть формата .docx")
        main_menu(message)
        return
    src = os.path.join('user_data/', str(message.from_user.id))
    ext = ".docx"
    in_name = src + ext
    downloaded_file = bot.download_file(file_info.file_path)

    with open(in_name, 'wb') as new_file:
        new_file.write(downloaded_file)
    doc = Document(in_name)
    all_tables = doc.tables
    data_tables = {i: None for i in range(len(all_tables))}
    for i, table in enumerate(all_tables):
        data_tables[i] = [[] for _ in range(len(table.rows))]
        for j, row in enumerate(table.rows):
            for cell in row.cells:
                data_tables[i][j].append(cell.text)

    print(data_tables)
    data_tables_str = ""
    for i in data_tables:
        for j in data_tables[i]:
            data_tables_str += ';'.join(j)
        data_tables_str += '\n'

    messages = [{"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"""### Задание ###
    Представлена таблица - в одной строке вся информация об отдельно взятой продаже. 
    Создай таблицу с 4 столбцами. в первом - артикул. во втором, денежный объем его продаж.
    в третьем, суммарный объем его продаж в штуках. в четвертом, 
    его остаток на самый последний момент. 
    Ответа приведи в виде таблицы в csv формате разделитель ; 
    названия столбцов пиши кроме таблицы ничего не пиши
    ### Таблица ###
    {data_tables_str}"""}]
    completion = client.chat.completions.create(
        model=type_network,
        messages=messages
    )
    os.remove(in_name)
    bot.delete_message(message.from_user.id, msg_temp)
    df = pd.read_csv(StringIO(str(completion.choices[0].message.content)), sep=';')

    df.to_excel(f'user_data/{message.from_user.id}_output.xlsx', index=False)

    with open(f'user_data/{message.from_user.id}_output.xlsx', 'rb') as f1:
        bot.send_document(message.chat.id, f1)


@bot.message_handler(content_types=["document"])
def handle_document(message):
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
    if user.prompt == 'word-table':
        if message.document.file_size > 100 * 1000 * 1000:
            bot.delete_message(message.from_user.id, msg_temp)
            bot.send_message(message.from_user.id, "Файл должен быть меньше 100 Мб")
            main_menu(message)
            return
        file_info = bot.get_file(message.document.file_id)
        if file_info.file_path[file_info.file_path.rfind('.'):] != '.docx':
            bot.delete_message(message.from_user.id, msg_temp)
            bot.send_message(message.from_user.id, "Файл должен быть формата .docx")
            main_menu(message)
            return
        src = os.path.join('user_data/', str(message.from_user.id))
        ext = ".docx"
        in_name = src + ext
        downloaded_file = bot.download_file(file_info.file_path)

        with open(in_name, 'wb') as new_file:
            new_file.write(downloaded_file)
        doc = Document(in_name)
        all_tables = doc.tables
        data_tables = {i: None for i in range(len(all_tables))}
        for i, table in enumerate(all_tables):
            data_tables[i] = [[] for _ in range(len(table.rows))]
            for j, row in enumerate(table.rows):
                for cell in row.cells:
                    data_tables[i][j].append(cell.text)

        print(data_tables)
        data_tables_str = ""
        for i in data_tables:
            for j in data_tables[i]:
                data_tables_str += ';'.join(j)
            data_tables_str += '\n'

        messages = [{"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"""### Задание ###
Представлена таблица - в одной строке вся информация об отдельно взятой продаже. 
Создай таблицу с 4 столбцами. в первом - артикул. во втором, денежный объем его продаж.
в третьем, суммарный объем его продаж в штуках. в четвертом, 
его остаток на самый последний момент. 
Ответа приведи в виде таблицы в csv формате разделитель ; 
названия столбцов пиши кроме таблицы ничего не пиши
### Таблица ###
{data_tables_str}"""}]
        completion = client.chat.completions.create(
            model=type_network,
            messages=messages
        )
        os.remove(in_name)
        bot.delete_message(message.from_user.id, msg_temp)
        df = pd.read_csv(StringIO(str(completion.choices[0].message.content)), sep=';')

        df.to_excel(f'user_data/{message.from_user.id}_output.xlsx', index=False)

        with open(f'user_data/{message.from_user.id}_output.xlsx', 'rb') as f1:
            bot.send_document(message.chat.id, f1)
    elif user.prompt == 'table-table':
        if message.document.file_size > 100 * 1000 * 1000:
            bot.delete_message(message.from_user.id, msg_temp)
            bot.send_message(message.from_user.id, "Файл должен быть меньше 100 Мб")
            main_menu(message)
            return
        file_info = bot.get_file(message.document.file_id)
        if file_info.file_path[file_info.file_path.rfind('.'):] != '.xlsx':
            bot.delete_message(message.from_user.id, msg_temp)
            bot.send_message(message.from_user.id, "Файл должен быть формата .xlsx")
            main_menu(message)
            return
        src = os.path.join('user_data/', str(message.from_user.id))
        ext = ".docx"
        in_name = src + ext
        downloaded_file = bot.download_file(file_info.file_path)

        with open(in_name, 'wb') as new_file:
            new_file.write(downloaded_file)
        df = pd.read_excel(in_name)

        data_tables_str = df.to_csv(index=False, sep=';')

        messages = [{"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"""### Задание ###
Представлена таблица - в одной строке вся информация об отдельно взятой продаже. 
Создай таблицу с 4 столбцами. в первом - артикул. во втором, денежный объем его продаж.
в третьем, суммарный объем его продаж в штуках. в четвертом, 
его остаток на самый последний момент. 
Ответа приведи в виде таблицы в csv формате разделитель ; 
названия столбцов пиши кроме таблицы ничего не пиши
### Таблица ###
{data_tables_str}"""}]
        completion = client.chat.completions.create(
            model=type_network,
            messages=messages
        )
        os.remove(in_name)
        bot.delete_message(message.from_user.id, msg_temp)
        df = pd.read_csv(StringIO(str(completion.choices[0].message.content)), sep=';')

        df.to_excel(f'user_data/{message.from_user.id}_output.xlsx', index=False)

        with open(f'user_data/{message.from_user.id}_output.xlsx', 'rb') as f1:
            bot.send_document(message.chat.id, f1)
    else:
        bot.delete_message(message.from_user.id, msg_temp)
        bot.send_message(message.from_user.id, 'Выберете требуемый режим')
        main_menu(message)
        return


bot.polling()
