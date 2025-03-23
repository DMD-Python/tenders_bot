import logging
import os
import sys
from threading import Thread

from django.apps import AppConfig
from django.db import DatabaseError

logger = logging.getLogger(__name__)


class TendersConfig(AppConfig):
    name = "tenders_bot"
    default_auto_field = "django.db.models.BigAutoField"
    root_node = None

    def __init__(self, app_name, app_module):
        super().__init__(app_name, app_module)

    def ready(self):
        if os.path.basename(sys.argv[0]) == "manage.py" and sys.argv[1] == "runserver":
            start_app()


def start_app():
    logger.info("Starting tenders_bot app")
    try:
        setup_node_tree()
        start_telegram_bot()
    except DatabaseError:
        logger.exception(f"Database error on startup")
        raise
    logger.info("Started tenders_bot app")


def setup_node_tree():
    from tenders_bot.models import Node

    logger.info("Recalculating node tree")
    TendersConfig.root_node = Node.objects.filter(parent_node__isnull=True).first()
    TendersConfig.root_node.save(update_fields=["path"])
    logger.info("Successfully updated node tree")


def start_telegram_bot(*args, **kwargs):
    from tenders_bot.telegram import telegram_bot_main

    logger.info("Starting telegram bot")
    Thread(daemon=True, target=telegram_bot_main, args=args, kwargs=kwargs).start()
    logger.info("Telegram bot thread running")