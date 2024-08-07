import os

import telebot
from telebot.apihelper import ApiException


class TelegramSender:
    def __init__(self):
        BOT_TOKEN = os.environ.get("BOT_TOKEN")
        CHAT_ID = os.environ.get("CHAT_ID")

        self.tb = telebot.TeleBot(token=BOT_TOKEN, parse_mode="Markdown")
        self.chat_id = CHAT_ID

    def send_message(self, message):
        try:
            mess = self.tb.send_message(chat_id=self.chat_id, text=message)
            return mess
        except ApiException as e:
            return e


bot = TelegramSender()
