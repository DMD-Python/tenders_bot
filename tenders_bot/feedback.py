import logging
import os
from io import BytesIO

import telebot
from django.core.files import File
from django.core.mail import EmailMessage, get_connection
from django.utils.formats import localize
from django.utils.timezone import localtime
from telebot.apihelper import ApiTelegramException

from tenders_bot.models import Feedback, UserUploadedFile
from tenders_bot.settings import DEFAULT_FROM_EMAIL, ID_FORMAT, MAIL_FEEDBACK_TO, MAX_FILE_SIZE_MB, MAX_TOTAL_SIZE_MB
from tenders_bot.telegram import bot, finish_input, user_states

logger = logging.getLogger(__name__)

messages = {
    "company": "Введите название компании:",
    "inn": "Введите ИНН компании:",
    "name": "Введите ФИО:",
    "email": "Введите контактный email:",
    "contact_number": "Введите контактный номер телефона:",
    "text": "Введите ваш запрос:",
    "files": "Можете прикрепить файлы (по одному, весом не больше 3Мб каждый и 15Мб суммарно) или отправить обращение.",
    "confirm": "Обращение заполнено. Отправить?",
}

type_to_fields = {
    Feedback.FeedbackType.GENERAL: ["company", "inn", "name", "email", "contact_number", "text", "files"],
    Feedback.FeedbackType.CONTRACT_TEMPLATE_SUPPLIER: ["company", "inn", "email", "confirm"],
    Feedback.FeedbackType.CONTRACT_TEMPLATE_CONTRACTOR: ["company", "inn", "email", "confirm"],
}


def contract_template_supplier_start(chat_id, _):
    _feedback_start(chat_id, _, Feedback.FeedbackType.CONTRACT_TEMPLATE_SUPPLIER)


def contract_template_contractor_start(chat_id, _):
    _feedback_start(chat_id, _, Feedback.FeedbackType.CONTRACT_TEMPLATE_CONTRACTOR)


def feedback_start(chat_id, _):
    _feedback_start(chat_id, _, Feedback.FeedbackType.GENERAL)


def _feedback_start(chat_id, _, feedback_type: Feedback.FeedbackType):
    existing_feedbacks = Feedback.objects.filter(telegram_chat_id=chat_id, submitted=False)
    existing_feedbacks.delete()

    new_feedback = Feedback.objects.create(
        telegram_chat_id=chat_id, type=feedback_type, next_field=type_to_fields[feedback_type][0]
    )
    user_states[chat_id].entering_feedback = True

    request_next_input(new_feedback)


def request_next_input(feedback):
    # Remove cancel button
    try:
        if feedback.telegram_sent_message_id:
            bot.edit_message_reply_markup(feedback.telegram_chat_id, feedback.telegram_sent_message_id)
    except ApiTelegramException as e:
        logger.exception("Exception while editing message")

    # Start new feedback
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Отмена", callback_data=f"cancel_feedback"))

    field = feedback.next_field

    if type_to_fields[feedback.type].index(field) == len(type_to_fields[feedback.type]) - 1:
        markup.add(telebot.types.InlineKeyboardButton("Отправить", callback_data=f"submit_feedback"))

    message = bot.send_message(feedback.telegram_chat_id, messages[field], reply_markup=markup)

    feedback.telegram_sent_message_id = message.id
    feedback.save()


@bot.message_handler(
    func=lambda message: message.chat.id in user_states and user_states[message.chat.id].entering_feedback,
    content_types=["text", "document", "photo"],
)
def feedback_process_input(message):
    feedback = Feedback.objects.get(telegram_chat_id=message.chat.id, submitted=False)
    field = feedback.next_field

    # Fill user info the first time
    if feedback.telegram_username is None:
        feedback.telegram_username = message.from_user.username
        feedback.telegram_first_name = message.from_user.first_name
        feedback.telegram_last_name = message.from_user.last_name

    # Process message contents

    # TODO: remove hardcode
    if field == "files":
        if message.document:
            feedback_process_file(message.document.file_id, message.document.file_name, message.chat.id)

        if message.photo:
            photo_size = message.photo[-1]
            feedback_process_file(photo_size.file_id, photo_size.file_id, message.chat.id)

        if message.caption or message.text:
            bot.send_message(message.chat.id, "На этом этапе можно загрузить только файлы, текст записан не будет.")
    else:
        if message.document or message.photo:
            if "files" in type_to_fields[feedback.type]:
                bot.send_message(
                    message.chat.id,
                    "Файлы можно будет прикрепить в конце обращения, пока что можно ввести только текст.",
                )
            else:
                bot.send_message(message.chat.id, 'Файлы можно прикрепить только в разделе "Обратная связь"')
        else:
            next_field_index = type_to_fields[feedback.type].index(field) + 1
            if next_field_index < len(type_to_fields[feedback.type]):
                setattr(feedback, field, message.text)
                feedback.next_field = type_to_fields[feedback.type][next_field_index]
            else:
                bot.send_message(message.chat.id, "Дополнить обращение уже нельзя, можно только отправить новое.")

    feedback.save()
    request_next_input(feedback)


def feedback_process_file(telegram_file_id, file_name, chat_id):
    file_info = bot.get_file(telegram_file_id)
    extension = os.path.splitext(file_info.file_path)[-1]
    file_name = os.path.splitext(file_name)[0]
    file_name = file_name + extension
    if extension == ".exe" or extension == ".bat" or extension == ".com" or extension == ".cmd":
        bot.send_message(
            chat_id,
            f"Файл с таким расширением расширением не допустим"
        )
        return
    file_size_in_bytes = file_info.file_size
    if file_size_in_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
        bot.send_message(
            chat_id,
            f"Файл под названием {file_name} не может быть загружен,"
            f" т.к. его размер превышает {MAX_FILE_SIZE_MB}Мб.",
        )
    else:
        feedback = Feedback.objects.get(telegram_chat_id=chat_id, submitted=False)
        existing_files_size = sum(f.file.size for f in feedback.uploaded_files.all())
        if existing_files_size + file_size_in_bytes > MAX_TOTAL_SIZE_MB * 1024 * 1024:
            bot.send_message(chat_id, f"Все файлы в обращении не могут превышать {MAX_TOTAL_SIZE_MB}Мб.")
        else:
            uploaded_file_bytes = bot.download_file(file_info.file_path)
            uploaded_file = File(BytesIO(uploaded_file_bytes), name=file_name)
            UserUploadedFile.objects.create(file=uploaded_file, feedback=feedback)
            bot.send_message(chat_id, f"Ваш файл {file_name} добавлен к обращению.")


def feedback_finish(feedback):
    feedback.submitted = True
    feedback.save()

    message = bot.send_message(feedback.telegram_chat_id, "Подождите немного, отправляем ваше обращение...")
    feedback_id = ID_FORMAT.format(id=feedback.id)
    try:
        email_feedback(feedback)
    except Exception as e:
        logger.exception("Exception while sending mail")

    bot.edit_message_text(
        f"Спасибо, ваш запрос принят!\nНомер обращения: {feedback_id}",
        message.chat.id,
        message.id,
    )
    logger.info(f"Accepted feedback {feedback_id}")

    user_states[feedback.telegram_chat_id].entering_feedback = False
    finish_input(feedback.telegram_chat_id)


@bot.callback_query_handler(func=lambda call: call.data == "cancel_feedback")
def feedback_cancel(call):
    feedback = Feedback.objects.get(telegram_chat_id=call.message.chat.id, submitted=False)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id)
    except ApiTelegramException as e:
        logger.exception("Exception while editing message")
    bot.send_message(call.message.chat.id, "Отправка обращения отменена")

    user_states[feedback.telegram_chat_id].entering_feedback = False
    finish_input(feedback.telegram_chat_id)


@bot.callback_query_handler(func=lambda call: call.data == "submit_feedback")
def feedback_submit(call):
    feedback = Feedback.objects.get(telegram_chat_id=call.message.chat.id, submitted=False)
    try:
        bot.edit_message_reply_markup(feedback.telegram_chat_id, feedback.telegram_sent_message_id)
    except ApiTelegramException as e:
        logger.exception("Exception while editing message")

    feedback_finish(feedback)


def email_feedback(feedback: Feedback):
    str_id = ID_FORMAT.format(id=feedback.id)
    # TODO: вынести формат в файл
    feedback_str = f"""
Пришло обращение из телеграм бота департамента тендеров и закупок.

Номер обращения: {str_id}.
Дата и время обращения: {localize(localtime(feedback.created_at))}

Название компании: {feedback.company}
ИНН: {feedback.inn}
ФИО: {feedback.name}
Номер телефона: {feedback.contact_number}
Электронная почта: {feedback.email}

Текст сообщения:
{feedback.text}
"""
    uploaded_files = feedback.uploaded_files.all()
    if uploaded_files:
        feedback_str = feedback_str + "\nВложенные файлы:\n- "
        feedback_str = feedback_str + "\n- ".join(
            os.path.basename(uploaded_file.file.name) for uploaded_file in feedback.uploaded_files.all()
        )
    logger.debug("Sending email")
    connection = get_connection(timeout=10)
    logger.debug("Established connection")
    mail = EmailMessage(
        f"Запрос из Telegram-бота: {str_id}",
        feedback_str,
        DEFAULT_FROM_EMAIL,
        MAIL_FEEDBACK_TO,
        connection=connection
    )
    for uploaded_file in feedback.uploaded_files.all():
        with uploaded_file.file.open('rb') as file:
            mail.attach(os.path.basename(uploaded_file.file.name), file.read())

    logger.debug("Created email")

    mail.send()
    logger.debug("Sent email")