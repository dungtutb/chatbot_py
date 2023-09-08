import asyncio
import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from telebot.async_telebot import AsyncTeleBot

load_dotenv()

url = 'https://tizi.asia/core-api/orders?payload={"limit":10,"offset":0,"search":"","orders":{"createdTime":"desc"},"filters":[{"key":"marketId","operator":"equal_to","value":"60e71dc1563671002b121783"}],"extraParams":{},"orderBy":"createdTime","orderType":"desc"}&offset=0&limit=50&orderBy=createdTime&orderType=desc'
TIZI_TOKEN = None
LIST_ITEM = {}
LAST_ITEM_FILE = "last_item.txt"
if os.path.exists(LAST_ITEM_FILE):
    with open(LAST_ITEM_FILE, "r") as f:
        LAST_ITEM_ID = f.read().strip()
else:
    LAST_ITEM_ID = ""
# CHATS = {749794702: {"id": 749794702, "notify": True}}
CHATS = {}
TIME_SLEEP = 1


def get_headers(token):
    return {"Authorization": "Bearer {}".format(token)}


def login():
    url = "https://tizi.asia/core-api/auth/login"

    payload = json.dumps(
        {
            "username": os.environ.get("USERNAME"),
            "password": os.environ.get("PASSWORD"),
            "deviceId": os.environ.get("DEVICEID"),
        }
    )
    headers = {"Content-Type": "application/json"}

    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        return response.json()["access_token"]


def get_token():
    global TIZI_TOKEN
    TIZI_TOKEN = login()


BOT_TOKEN = os.environ.get("BOT_TOKEN")

get_token()

print("Get token: {}\n".format(TIZI_TOKEN))

bot = AsyncTeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start", "hello"])
async def send_welcome(message):
    await bot.reply_to(message, "Howdy, how are you doing?")


@bot.message_handler(commands=["id"])
async def my_id(message):
    print(message.from_user.id)
    await bot.reply_to(message, str(message.from_user.id))


@bot.message_handler(commands=["on"])
async def turn_on_auto(message):
    if message.chat.id not in CHATS:
        CHATS[message.chat.id] = {"id": message.chat.id, "notify": True}
    else:
        CHATS[message.chat.id]["notify"] = True
    await bot.reply_to(message, "Turned on notification automatically!\n")


@bot.message_handler(commands=["off"])
async def turn_off_auto(message):
    if message.chat.id in CHATS:
        CHATS[message.chat.id]["notify"] = False
    await bot.reply_to(message, "Turned off notification!\n")


@bot.message_handler(commands=["status"])
async def get_status(message):
    await bot.reply_to(
        message,
        "Notification: {}\n".format("On" if message.chat.id in CHATS else "Off"),
    )


def process_date(t):
    return datetime.fromtimestamp(t / 1000.0).strftime("%d/%m/%Y %H:%M:%S")


async def reply_message(bot, message, result):
    if len(result) > 4095:
        for x in range(0, len(result), 4095):
            await bot.reply_to(message, text=result[x : x + 4095])
    else:
        await bot.reply_to(message, text=result)


async def send_message(bot, chat_id, result):
    if len(result) > 4095:
        for x in range(0, len(result), 4095):
            await bot.send_message(chat_id, text=result[x : x + 4095])
    else:
        await bot.send_message(chat_id, text=result)


def get_request():
    response = requests.request("GET", url, headers=get_headers(TIZI_TOKEN))
    if response.ok:
        return True, response.json()
    else:
        return False, response.text


def get_result_item(item):
    result = "Đơn hàng thị trường Phi\n"
    result += "ID: {} \n".format(item["orderId"])
    result += "Ngày tạo: {} \n".format(process_date(item["createdTime"]))
    result += "Ngày cập nhật: {} \n".format(process_date(item["updatedTime"]))
    result += "Ngày hủy: {} \n".format(
        process_date(item["hTime"]) if item["status"] else ""
    )
    result += "Tên sản phẩm: {} \n".format(item["productCombo"]["name"])
    result += "Tổng giá: {} \n".format(item["productCombo"]["localPrice"])
    result += "Trạng thái: {} \n".format("Hủy" if item["status"] else "")
    result += "TT hủy đơn: {} \n".format(item["invalidStatus"])
    result += "TT hủy đơn trùng: {} \n".format(item["customerRefusedStatus"])
    result += "Tên khách hàng: {} \n".format(item["customerName"])
    result += "Lời nhắn: {} \n".format(
        item["customerMessage"] if "customerMessage" in item else ""
    )
    # result += "Link: {} \n".format(item["orderRequest"]["link"])
    result += "utm_medium: {} \n".format(item["orderRequest"]["utm_medium"])
    result += "utm_source: {} \n".format(item["orderRequest"]["utm_source"])

    return result


@bot.message_handler(commands=["phi"])
async def send_welcome(message):
    status, items = get_request()
    if status is False:
        get_token()
        status, items = get_request()

    if status:
        if items and isinstance(items["items"], list):
            items["items"].reverse()
            for item in items["items"]:
                await reply_message(
                    bot,
                    message,
                    get_result_item(item),
                )
        else:
            await reply_message(bot, message, "Item is not list\n")
    else:
        await reply_message(bot, message, items[:300] + "\n")


@bot.message_handler(commands=["start", "hello"])
async def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")


@bot.message_handler(func=lambda msg: True)
async def echo_all(message):
    global LAST_ITEM_ID
    await reply_message(bot, message, LAST_ITEM_ID)


@bot.message_handler(commands=["last"])
async def lst_order(message):
    await bot.reply_to(message, "Turned off notification!\n")


# bot.infinity_polling()


async def update_new_items(notify=True):
    global LIST_ITEM, CHATS, LAST_ITEM_ID
    status, items = get_request()
    if status:
        if items and isinstance(items["items"], list):
            items["items"].reverse()
            for item in items["items"]:
                # LIST_ITEM[item["orderId"]] = item
                if item["orderId"] > LAST_ITEM_ID:
                    LAST_ITEM_ID = item["orderId"]
                    with open(LAST_ITEM_FILE, "w") as f:
                        f.write(LAST_ITEM_ID)
                    for v in CHATS.value():
                        if v["notify"]:
                            await send_message(
                                bot,
                                v["id"],
                                "###########  Đơn hàng mới  ###########\n "
                                + get_result_item(item),
                            )


async def periodic():
    global TIME_SLEEP
    while True:
        await update_new_items(True)
        await asyncio.sleep(TIME_SLEEP * 60)


async def main():
    await asyncio.gather(bot.polling(), periodic())


if __name__ == "__main__":
    asyncio.run(main())
