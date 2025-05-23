from __future__ import annotations

import dataclasses
import logging
from typing import Dict

import telebot
from django.conf import settings

from tenders_bot.apps import TendersConfig
from tenders_bot.models import Node
from tenders_bot.settings import TELEBOT_NUM_THREADS

logger = logging.getLogger(__name__)

# Создаем экземпляр бота
bot = telebot.TeleBot(settings.TELEGRAM_TOKEN, num_threads=TELEBOT_NUM_THREADS)

# Функция запуска бота
def telegram_bot_main(thread_patch_function=None):
    if thread_patch_function is not None:
        thread_patch_function()
    bot.infinity_polling(long_polling_timeout=5, timeout=10)  # запускается бот в бесконечный цикл


# Глобальный словарь состояний по chat_id
user_states: Dict[str, UserState] = {}

# Класс состояний пользователя
@dataclasses.dataclass
class UserState:
    return_to_node: Node = None
    entering_feedback: bool = True

# Сброс состояния пользователя
def reset_state(chat_id):
    user_states[chat_id] = UserState()


# Навигационные данные - сериализация переходов между узлами
@dataclasses.dataclass
class NavData:
    nav_to_node: Node
    direction: str  # 'r' for root, 'b' for back, 'f' for forward
    PREFIX = "nav:"

    # Преобразуем объект в строку для callback_data
    def serialize(self) -> str:
        return f"{self.PREFIX}{self.nav_to_node.id}|{self.direction}"

    # Обратная операция: из строки получаем NavData
    @staticmethod
    def deserialize(data: str):
        if not NavData.check(data):
            raise ValueError("Invalid data format, missing 'nav:' prefix")

        content = data[len(NavData.PREFIX) :]
        parts = content.split("|")

        node = Node.objects.get(id=int(parts[0]))

        return NavData(nav_to_node=node, direction=parts[1])

    @staticmethod
    def check(data: str) -> bool:
        return data.startswith(NavData.PREFIX)

# Обработка команды /start
@bot.message_handler(commands=["start"])
def start(message):
    logger.info(f'User entered "start": {message.from_user.username}')
    send_node(message.chat.id, TendersConfig.root_node, False)  # Отправка корневого узла

# Отправка узла пользователю
def send_node(chat_id, node, only_nav):
    node.refresh_from_db() # Обновляем данные узла
    reset_state(chat_id) # Сбрасываем состояние пользователя

    if not only_nav:
        if node.text:
            bot.send_message(chat_id, node.text, parse_mode="HTML", disable_web_page_preview=True)

        if len(node.files.all()) != 0:
            send_files(chat_id, node)

    if node.input_function:
        process_input_node(chat_id, node)
    else:
        send_navigation(chat_id, node)

# Отправка прикрепленных к узлу файлов
def send_files(chat_id, node):
    message = bot.send_message(chat_id, "Отправляем файлы, подождите немного...")
    for file in node.files.all():
        bot.send_document(chat_id, file.file)
    message_id = message.id if message else None
    bot.delete_message(chat_id, message_id)

# Отправка кнопок навигации
def send_navigation(chat_id, node):
    markup = telebot.types.InlineKeyboardMarkup()
    child_nodes = node.child_nodes.all()

    if len(child_nodes) == 0:
        if node.parent_node is None:
            logger.warning(f"Node {node.id} has neither a parent nor a child node")
        else:
            send_node(chat_id, node.parent_node, True)
        return

# Добавляем кнопки для дочерних узлов
    for child_node in child_nodes:
        nav_data = NavData(nav_to_node=child_node, direction="f")
        markup.add(telebot.types.InlineKeyboardButton(child_node.button_text, callback_data=nav_data.serialize()))

# Если родитель есть, то добавляем кнопку Назад
    if node.parent_node:
        back_nav_data = NavData(nav_to_node=node.parent_node, direction="b")
        markup.add(telebot.types.InlineKeyboardButton("Назад", callback_data=back_nav_data.serialize()))

# Если родитель не корневой узел, то добавляем кнопку "В начало"
        if node.parent_node != TendersConfig.root_node:
            to_root_nav_data = NavData(nav_to_node=TendersConfig.root_node, direction="r")
            markup.add(telebot.types.InlineKeyboardButton("В начало", callback_data=to_root_nav_data.serialize()))

    bot.send_message(chat_id, node.nav_text, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)

# Обработка навигации по кнопкам
@bot.callback_query_handler(func=lambda call: NavData.check(call.data))
def navigate(call):
    nav_data = NavData.deserialize(call.data)
    node = nav_data.nav_to_node

    # Для красивого отображения в интерфейсе
    if nav_data.direction == "f":
        where_to = node.button_text
    elif nav_data.direction == "b":
        where_to = "Назад"
    else:
        where_to = "В начало"

    new_text = call.message.text + "\n\n> " + where_to
    bot.edit_message_text(new_text, call.message.chat.id, call.message.id)

    send_node(call.message.chat.id, node, only_nav=nav_data.direction != "f")


# Обработка узлов где нужно вводить данные
# ----------- Input ----------- #
def process_input_node(chat_id, node):
    from tenders_bot.feedback import feedback_start

    input_functions = {
        "feedback": feedback_start,
    }
    if node.input_function in input_functions:
        user_states[chat_id].return_to_node = node
        input_functions[node.input_function](chat_id, node)
    else:
        raise ValueError("There is a node in the database, for which input function does not exist.")

# Завершение ввода данных — возврат к навигации
def finish_input(chat_id):
    node = user_states[chat_id].return_to_node
    send_navigation(chat_id, node)