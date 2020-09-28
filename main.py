from pymongo import MongoClient
from telebot import TeleBot, types
from collections import defaultdict

START, DESC, PHOTO, ADDLOC, CONFIRM = range(5)

LOCATIONS = defaultdict(lambda: {})
GOOGLE_API = "AIzaSyALtT3KbITF21-_amA_5midSpR0wcB96I8"

token = "1196220206:AAGvBHTUREy5Qpt_W9hwhO95uaSnN_oGZbA"

bot = TeleBot(token)
client = MongoClient('localhost', 27017)
db = client['Telegram']
loc_collection = db['locations']
state_collection = db['state']
yes_no_keyboard = types.InlineKeyboardMarkup(row_width=2)
yes_button = types.InlineKeyboardButton(text="Да", callback_data="Yes")
no_button = types.InlineKeyboardButton(text="Нет", callback_data="No")
yes_no_keyboard.add(yes_button, no_button)


def insert_record(collection, data):
    return collection.insert_one(data).inserted_id


def delete_record(collection, element, multiple=True):
    if multiple:
        results = collection.delete_many(element)
        return [r for r in results]
    else:
        return collection.delete_one(element)


def get_record(collection, element, multiple=True):
    if multiple:
        results = collection.find(element)
        return [r for r in results]
    else:
        return [collection.find_one(element)]


def update_record(collection, query_elements, new_values):
    collection.update_one(query_elements, {'$set': new_values})


def update_location(user_id, key, value):
    LOCATIONS[user_id][key] = value


def get_location(user_id):
    return LOCATIONS.pop(user_id, None)


def set_state(message, state):
    try:
        update_record(state_collection, {"id": message.chat.id}, {"state": state})
    except:
        insert_record(state_collection, {"id": message.chat.id, "state": state})


def get_state(message):
    try:
        state = get_record(state_collection, {"id": message.chat.id})
        return state[0]["state"]
    except:
        return START


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
    bot.send_message(message.chat.id, "Добавьте описание места")
    set_state(message, DESC)


@bot.message_handler(func=lambda message: get_state(message) == DESC)
def add_desc_handlers(message):
    update_location(message.chat.id, "desc", message.text)
    bot.send_message(message.chat.id, "Отправьте фотографию или любое сообщение для добавления без фото")
    set_state(message, PHOTO)


@bot.message_handler(func=lambda message: get_state(message) == PHOTO, content_types=['photo'])
def add_photo_handlers(message):
    file_info = bot.get_file(message.photo[len(message.photo) - 1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    update_location(message.chat.id, "photo", downloaded_file)

    bot.send_message(message.chat.id, "Отправьте локацию или любое сообщение для добавления без локации")
    set_state(message, ADDLOC)


@bot.message_handler(func=lambda message: get_state(message) == PHOTO)
def add_no_photo_handlers(message):
    update_location(message.chat.id, "photo", "")
    bot.send_message(message.chat.id, "Отправьте локацию или любое сообщение для добавления без локации")
    set_state(message, ADDLOC)


@bot.message_handler(func=lambda message: get_state(message) == ADDLOC, content_types=["text", "location"])
def add_loc_handlers(message):
    if message.location:
        update_location(message.chat.id, "loc", {"lat": message.location.latitude,
                                                 "lon": message.location.longitude})
    else:
        update_location(message.chat.id, "loc", "")

    record = LOCATIONS[message.chat.id]
    bot.send_message(message.chat.id, record["desc"])
    if record["photo"] != "":
        bot.send_photo(message.chat.id, record["photo"])
    if record["loc"] != "":
        bot.send_location(message.chat.id, record["loc"]["lat"], record["loc"]["lon"])

    bot.send_message(message.chat.id, "Добавляем запись?", reply_markup=yes_no_keyboard)
    set_state(message, CONFIRM)


@bot.callback_query_handler(func=lambda message: get_state(message.message) == CONFIRM)
def add_confirm_handlers(callback_query):
    message = callback_query.message
    text = callback_query.data
    record = get_location(message.chat.id)
    if text == "Yes":
        insert_record(loc_collection, record)
        bot.send_message(message.chat.id, "Запись добавлена")
    elif text == "No":
        bot.send_message(message.chat.id, "Добавление записи отменено")
    set_state(message, START)


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
