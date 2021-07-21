from pymongo import MongoClient
from telebot import TeleBot, types
from collections import defaultdict
from haversine import haversine, Unit
import os

START, DESC, PHOTO, ADDLOC, CONFIRM = range(5)

LOCATIONS = defaultdict(lambda: {})

token = ""

bot = TeleBot(token)
client = MongoClient(os.getenv("MONGO_URI"))
db = client['Telegram']
loc_collection = db['locations']
state_collection = db['state']
yes_no_keyboard = types.InlineKeyboardMarkup(row_width=2)
yes_button = types.InlineKeyboardButton(text="Да", callback_data="Yes")
no_button = types.InlineKeyboardButton(text="Нет", callback_data="No")
yes_no_keyboard.add(yes_button, no_button)


def get_distance(orig, dest):
    return haversine(orig, dest, unit=Unit.METERS)


def insert_record(collection, data):
    return collection.insert_one(data).inserted_id


def delete_record(collection, element, multiple=True):
    if multiple:
        results = collection.delete_many(element)
        return results
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
    result = get_record(state_collection, {"id": message.chat.id})
    if len(result) > 0:
        update_record(state_collection, {"id": message.chat.id}, {"state": state})
    else:
        insert_record(state_collection, {"id": message.chat.id, "state": state})


def get_state(message):
    try:
        state = get_record(state_collection, {"id": message.chat.id}, multiple=False)
        return state[0]["state"]
    except:
        return START


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    set_state(message, START)
    bot.send_message(message.chat.id, "Бот позволяет добавлять интересные места\n"
                                      "При отправке геопозиции выводит до 10 мест в радиусе 500 метров\n"
                                      "/add позволяет пошагово добавить место\n"
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
    bot.send_message(message.chat.id, "Добавить фотографию?", reply_markup=yes_no_keyboard)
    set_state(message, PHOTO)


@bot.callback_query_handler(func=lambda message: get_state(message.message) == PHOTO)
def choise_photo_handler(callback_query):
    message = callback_query.message
    text = callback_query.data
    if text == "Yes":
        bot.send_message(message.chat.id, "Отправьте фотографию")
        set_state(message, PHOTO)
    elif text == "No":
        bot.send_message(message.chat.id, "Отправьте геопозицию, эти данные являются обязательными")
        update_location(message.chat.id, "photo", "")
        set_state(message, ADDLOC)


@bot.message_handler(func=lambda message: get_state(message) == PHOTO, content_types=['photo'])
def add_photo_handlers(message):
    file_info = bot.get_file(message.photo[len(message.photo) - 1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    update_location(message.chat.id, "photo", downloaded_file)
    bot.send_message(message.chat.id, "Отправьте геопозицию, эти данные являются обязательными")
    set_state(message, ADDLOC)


@bot.message_handler(func=lambda message: get_state(message) == PHOTO)
def add_no_photo_handlers(message):
    update_location(message.chat.id, "photo", "")
    bot.send_message(message.chat.id, "Вы не отправили фотографию, локация будет добавлена без фото. Отправьте геопозицию")
    set_state(message, ADDLOC)


@bot.message_handler(func=lambda message: get_state(message) == ADDLOC, content_types=["location"])
def add_loc_handlers(message):
    update_location(message.chat.id, "loc", {"lat": message.location.latitude,
                                             "lon": message.location.longitude})

    record = LOCATIONS[message.chat.id]
    bot.send_message(message.chat.id, record["desc"])
    if record["photo"] != "":
        bot.send_photo(message.chat.id, record["photo"])
    if record["loc"] != "":
        bot.send_location(message.chat.id, record["loc"]["lat"], record["loc"]["lon"])

    bot.send_message(message.chat.id, "Добавляем запись?", reply_markup=yes_no_keyboard)
    set_state(message, CONFIRM)


@bot.message_handler(func=lambda message: get_state(message) == ADDLOC)
def add_empty_loc_handlers(message):
    bot.send_message(message.chat.id, "Укажите геопозицию, эти данные являются обязательными")


@bot.callback_query_handler(func=lambda message: get_state(message.message) == CONFIRM)
def add_confirm_handlers(callback_query):
    message = callback_query.message
    text = callback_query.data
    record = get_location(message.chat.id)
    record["id"] = message.chat.id
    if text == "Yes":
        insert_record(loc_collection, record)
        bot.send_message(message.chat.id, "Запись добавлена")
    elif text == "No":
        bot.send_message(message.chat.id, "Добавление записи отменено")
    set_state(message, START)


@bot.message_handler(commands=['list'])
def list_handlers(message):
    bot.send_message(message.chat.id, "Сохраненные места")
    places = get_last_places(message)
    if len(places) > 10:
        start_index = len(places) - 10
        places = places[start_index:]
    if len(places) == 0:
        bot.send_message(message.chat.id, "У вас нет запомненных мест")
    else:
        send_places(message, places)


def send_places(message, places):
    count = 1
    for place in places:
        if place.get("dist", None) is not None:
            text = "{}. {} ({}м.)".format(count, place["desc"], int(place["dist"]))
        else:
            text = "{}. {}".format(count, place["desc"])
        if place["photo"] != "":
            bot.send_photo(message.chat.id, place["photo"], caption=text)
        else:
            bot.send_message(message.chat.id, text)
        if place["loc"] != "":
            bot.send_location(message.chat.id, place["loc"]["lat"], place["loc"]["lon"])
        count += 1


@bot.message_handler(commands=['reset'])
def reset_handlers(message):
    delete_record(loc_collection, {"id": message.chat.id})
    bot.send_message(message.chat.id, "Все сохраненные места удалены")


@bot.message_handler(func=lambda message: get_state(message) == START, content_types=["location"])
def near_places_handler(message):
    bot.send_message(message.chat.id, "Сохраненные места")
    places = get_near_places(message, message.location)
    if len(places) > 10:
        start_index = len(places) - 10
        places = places[start_index:]
    if len(places) == 0:
        bot.send_message(message.chat.id, "В радиусе 500м. нет запомненных мест")
    else:
        send_places(message, places)


def get_last_places(message):
    return get_record(loc_collection, {"id": message.chat.id})


def get_near_places(message, location):
    orig = (location.latitude, location.longitude)
    result = []
    places = get_record(loc_collection, {"id": message.chat.id, "loc": {"$ne": ""}})
    for place in places:
        dest = (place["loc"]["lat"], place["loc"]["lon"])
        dist = get_distance(orig, dest)
        if dist <= 500:
            place["dist"] = dist
            result.append(place)
    return result


if __name__ == "__main__":
    bot.polling()
