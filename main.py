import datetime

import telebot
from openai import OpenAI

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


@bot.message_handler(commands=['start'])
def start(message: telebot.types.Message) -> None:
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not (user is None):
        bot.send_message(message.from_user.id, bot_answer[lang]["start_ok"])
    else:
        bot.send_message(message.from_user.id, bot_answer[lang]["not_authorization"])


@bot.message_handler(commands=['help'])
def help_message(message: telebot.types.Message) -> None:
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not (user is None):
        if user.company_id != 0:
            bot.send_message(message.from_user.id, bot_answer[lang]["help"])
        else:
            bot.send_message(message.from_user.id, bot_answer[lang]["help_admin"])
    else:
        bot.send_message(message.from_user.id, bot_answer[lang]["not_authorization"])


# Authorization
@bot.message_handler(commands=['authorization'])
def authorization(message: telebot.types.Message) -> None:
    bot.send_message(message.from_user.id, bot_answer[lang]["authorization_name"])
    bot.register_next_step_handler(message, authorization_name)


def authorization_name(message: telebot.types.Message) -> None:
    bot.send_message(message.from_user.id, bot_answer[lang]["authorization_password"])
    bot.register_next_step_handler(message, authorization_password, message.text)


def authorization_password(message: telebot.types.Message, company_name: str) -> None:
    db_sess = db_session.create_session()
    company = db_sess.query(Company).filter(Company.company_name == company_name).first()
    if not (company is None) and company.check_password(message.text):
        user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
        if user is None:
            user_count = len(db_sess.query(CompanyUser).filter(CompanyUser.company_id ==
                                                               company.company_id).all())
            if user_count < company.max_num_users:
                company.max_num_users += 1
                user_company = CompanyUser()
                user = User()
                user.telegram_id = user_company.telegram_id = message.from_user.id
                user.company_id = user_company.company_id = company.company_id
            else:
                bot.send_message(message.from_user.id, bot_answer[lang]["authorization_fail_1"])
                return
            db_sess.add(user)
            db_sess.add(user_company)
        else:
            user.company_id = company.company_id
        db_sess.commit()
        bot.send_message(message.from_user.id, bot_answer[lang]["authorization_success"])
    else:
        bot.send_message(message.from_user.id, bot_answer[lang]["authorization_fail"])


@bot.message_handler(commands=['log_out'])
def log_out(message: telebot.types.Message) -> None:
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not (user is None):
        db_sess.delete(user)
        db_sess.commit()
    bot.send_message(message.from_user.id, bot_answer[lang]["logout_success"])


# Set mode

@bot.message_handler(commands=['settings'])
def settings(message: telebot.types.Message) -> None:
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()

    if user is None:
        bot.send_message(message.from_user.id, bot_answer[lang]["not_authorization"])
        return
    prompts = db_sess.query(Prompt).all()
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i in prompts:
        keyboard.row(i.description)
    bot.send_message(message.from_user.id, bot_answer[lang]["prompt"], reply_markup=keyboard)


def prompt(message: telebot.types.Message) -> None:
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    prompt_ = db_sess.query(Prompt).filter(Prompt.description == message.text).first()
    if prompt_ is None:
        bot.send_message(message.from_user.id, bot_answer[lang]["incorrect_prompt"])
    else:
        user.prompt = prompt_.prompt
        db_sess.commit()
        bot.send_message(message.from_user.id, bot_answer[lang]["success_prompt"])
        bot.register_next_step_handler(message, text_handler)


# Administration

@bot.message_handler(commands=['delete'])
def admin_delete_company_start(message: telebot.types.Message) -> None:
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    if user is None:
        bot.send_message(message.from_user.id, bot_answer[lang]["not_authorization"])
        return
    if user.company_id != 0:
        bot.send_message(message.from_user.id, bot_answer[lang]["start_ok"])
        return
    bot.send_message(message.from_user.id, bot_answer[lang]["choose_company"])
    bot.register_next_step_handler(message, admin_delete_company_confirm)


def admin_delete_company_confirm(message: telebot.types.Message) -> None:
    db_sess = db_session.create_session()
    company = db_sess.query(Company).filter(Company.company_name == message.text).first()
    if company is None:
        bot.send_message(message.from_user.id, bot_answer[lang]["unreal_company"])
        return
    bot.send_message(message.from_user.id, bot_answer[lang]["confirm"], reply_markup=keyboard_confirm)
    bot.register_next_step_handler(message, admin_delete_company, (company.company_name,))


def admin_delete_company(message: telebot.types.Message, data: tuple) -> None:
    """
    :param message:
    :param data: name company
    :return:
    """
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
    bot.send_message(message.from_user.id, bot_answer[lang]["ok"])


@bot.message_handler(commands=['add'])
def admin_add_company_start(message: telebot.types.Message) -> None:
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    if user is None:
        bot.send_message(message.from_user.id, bot_answer[lang]["not_authorization"])
        return
    if user.company_id != 0:
        bot.send_message(message.from_user.id, bot_answer[lang]["start_ok"])
        return
    bot.send_message(message.from_user.id, bot_answer[lang]["input_name_company"])
    bot.register_next_step_handler(message, admin_add_company_password)


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
            bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
            return

    bot.send_message(message.from_user.id, bot_answer[lang]["ok"])


@bot.message_handler(commands=['update_limit'])
def admin_update_limit_user_start(message: telebot.types.Message) -> None:
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    if user is None:
        bot.send_message(message.from_user.id, bot_answer[lang]["not_authorization"])
        return
    if user.company_id != 0:
        bot.send_message(message.from_user.id, bot_answer[lang]["start_ok"])
        return
    bot.send_message(message.from_user.id, bot_answer[lang]["input_name_company"])
    bot.register_next_step_handler(message, admin_update_limit_user_limit)


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
    if message.text == bot_answer[lang]["confirm"]:
        try:
            db_sess = db_session.create_session()
            company = db_sess.query(Company).filter(Company.company_name == data[0]).first()
            if company is None:
                bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
                return
            company[0].max_num_users = data[1]
            db_sess.commit()
        except ValueError:
            bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
            return

    bot.send_message(message.from_user.id, bot_answer[lang]["ok"])


@bot.message_handler(commands=['update_date'])
def admin_update_date_start(message: telebot.types.Message) -> None:
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()
    if user is None:
        bot.send_message(message.from_user.id, bot_answer[lang]["not_authorization"])
        return
    if user.company_id != 0:
        bot.send_message(message.from_user.id, bot_answer[lang]["start_ok"])
        return
    bot.send_message(message.from_user.id, bot_answer[lang]["input_name_company"])
    bot.register_next_step_handler(message, admin_update_date_date)


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
    if message.text == bot_answer[lang]["confirm"]:
        try:
            db_sess = db_session.create_session()
            company = db_sess.query(Company).filter(Company.company_name == data[0]).first()
            if company is None:
                bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
                return
            company[0].set_time(time=data[1])
            db_sess.commit()
        except ValueError:
            bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
            return

    bot.send_message(message.from_user.id, bot_answer[lang]["ok"])


@bot.message_handler(commands=['add_prompt'])
def admin_add_prompt_start(message: telebot.types.Message) -> None:
    bot.send_message(message.from_user.id, bot_answer[lang]["input_prompt"])
    bot.register_next_step_handler(message, admin_add_prompt_description)


def admin_add_prompt_description(message: telebot.types.Message) -> None:
    bot.send_message(message.from_user.id, bot_answer[lang]["input_description"])
    bot.register_next_step_handler(message, admin_add_prompt_confirm, message.text)


def admin_add_prompt_confirm(message: telebot.types.Message, prompt_text: str) -> None:
    bot.send_message(message.from_user.id, bot_answer[lang]["confirm"], reply_markup=keyboard_confirm)
    bot.register_next_step_handler(message, admin_add_prompt, (prompt_text, message.text))


def admin_add_prompt(message: telebot.types.Message, prompt_all: tuple) -> None:
    if message.text == bot_answer[lang]["confirm"]:
        try:
            db_sess = db_session.create_session()
            prompt_ = Prompt()
            prompt_.prompt = prompt_all[0]
            prompt_.description = prompt_all[1]
            db_sess.add(prompt_)
            db_sess.commit()
        except ValueError:
            bot.send_message(message.from_user.id, bot_answer[lang]["input_incorrect"])
            return

    bot.send_message(message.from_user.id, bot_answer[lang]["ok"])


@bot.message_handler(content_types=["text"])
def text_handler(message: telebot.types.Message) -> None:
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.telegram_id == message.from_user.id).first()

    if user is None:
        bot.send_message(message.from_user.id, bot_answer[lang]["not_authorization"])
        return
    if user.company.time <= datetime.datetime.now():
        bot.send_message(message.from_user.id, bot_answer[lang]["end_time"])
        return
    completion = client.chat.completions.create(
        model=type_network,
        messages=[
            {"role": "user", "content": user.prompt + message.text}
        ]
    )
    bot.send_message(message.from_user.id, str(completion.choices[0].message.content))


bot.polling()
