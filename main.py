from pymongo import MongoClient
from telebot import TeleBot
import pymongo

START, DESC, PHOTO, LOC, CONFIRM = range(5)

token = "1196220206:AAGvBHTUREy5Qpt_W9hwhO95uaSnN_oGZbA"

bot = TeleBot(token)
client = MongoClient('localhost', 27017)
db = client['Telegram']
loc_collection = db['locations']
state_collection = db['state']


def insert_record(collection, data):
    return collection.insert_one(data).inserted_id


def get_record(collection, element, multiple=True):
    if multiple:
        results = collection.delete_many(element)
        return [r for r in results]
    else:
        return collection.delete_one(element)


def delete_record(collection, element, multiple=True):
    if multiple:
        results = collection.find(element)
        return [r for r in results]
    else:
        return [collection.find_one(element)]


def update_record(collection, query_elements, new_values):
    collection.update_one(query_elements, {'$set': new_values})


def set_state(message, state):
    update_record(state_collection, message.chat.id, {"state": state})


def get_state(message):
    state = get_record(state_collection, message.chat.id, multiple=False)
    return state[0]["state"]


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    set_state(message, START)
    bot.send_message(message.chat.id, "Бот позволяет добавлять интересные места\n"
                                      "/add позволяет добавить место\n"
                                      "/list выводит список 10 последних добавленных мест\n"
                                      "/reset позволяет очистить добавленные места\n"
                     )


@bot.message_handler(commands=['add'])
def add_handlers(message):
    set_state(message, DESC)
    bot.send_message(message.chat.id, "Добавьте описание места")


@bot.message_handler(func=lambda message: get_state(message) == DESC)
def add_desc_handlers(message):
    # TODO Реализовать добавление описания
    pass


@bot.message_handler(func=lambda message: get_state(message) == PHOTO)
def add_photo_handlers(message):
    # TODO Реализовать добавление фотографии
    pass


@bot.message_handler(func=lambda message: get_state(message) == LOC)
def add_loc_handlers(message):
    # TODO Реализовать добавление геопозиции
    pass


@bot.message_handler(func=lambda message: get_state(message) == CONFIRM)
def add_confirm_handlers(message):
    # TODO Реализовать подтвержение
    pass


@bot.message_handler(commands=['list'])
def list_handlers(message):
    # TODO Реализовать вывод списка локаций
    pass


@bot.message_handler(commands=['reset'])
def reset_handlers(message):
    # TODO Реализовать удаление локаций пользователя
    pass


if __name__ == "__main__":
    bot.polling()
