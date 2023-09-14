import asyncio
import json
import os
from datetime import datetime, timezone

import pytz
import requests
from dotenv import load_dotenv
from telebot.async_telebot import AsyncTeleBot

load_dotenv()

PHILIPPIN_MARKET = "phi"
MALAYSIA_MARKET = "malay"

MARKETS = {
    PHILIPPIN_MARKET: {
        "marketId": "60e71dc1563671002b121783",
        "title": "Đơn hàng thị trường: Phi\n",
    },
    MALAYSIA_MARKET: {
        "marketId": "60e71da9563671002b12177f",
        "title": "Đơn hàng thị trường: Malay\n",
    },
}
MYID = "633e83202837f9a4282e44ab"

TIZI_TOKEN = None
LIST_ITEM = {}
LAST_ITEM_FILE = "last_item.txt"
if os.path.exists(LAST_ITEM_FILE):
    with open(LAST_ITEM_FILE, "r") as f:
        LAST_ITEM_ID = f.read().strip()
else:
    LAST_ITEM_ID = ""
# CHATS = {5496851372: {"id": 5496851372, "notify": True}}
CHATS = {}
TIME_SLEEP = 60

TIME_ZONE = "Asia/Ho_Chi_Minh"


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
    global TIME_ZONE
    local = pytz.timezone(TIME_ZONE)
    naive = datetime.fromtimestamp(t / 1000.0, local)
    return naive.strftime("%d/%m/%Y %H:%M:%S")


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


def get_request(url):
    try:
        response = requests.request("GET", url, headers=get_headers(TIZI_TOKEN))
        if response.ok:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)


def get_list_user():
    payload = {
        "limit": -1,
        "extraParams": {"g": True},
        "filters": [{"key": "roles", "operator": "equal_to", "value": "mkt"}],
    }
    url = "https://tizi.asia/core-api/users?payload={}".format(
        json.dumps(payload, separators=(",", ":"))
    )
    return get_request(url)


def get_statistic(day: datetime):
    startDate = int(
        day.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000
    )
    day.replace(hour=23, minute=59, second=59)
    endDate = int(
        day.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp()
        * 1000
    )

    payload = {
        "extraParams": {"g": True},
        "findRequest": {
            "filters": [
                {
                    "key": "createdTime",
                    "operator": "greater_than_or_equal_to",
                    "value": startDate,
                    "id": "startDate",
                },
                {
                    "key": "createdTime",
                    "operator": "less_than_or_equal_to",
                    "value": endDate,
                    "id": "endDate",
                },
                {
                    "key": "tiktokIsSampleRequest",
                    "operator": "not_equal_to",
                    "value": False,
                    "id": "tiktokIsSampleRequest",
                },
                {
                    "key": "marketId",
                    "operator": "in",
                    "value": [
                        "60e71da9563671002b12177f",
                        "60e71dc1563671002b121783",
                        "60ec0fe83b90ec002a2b5c63",
                        "61061da933ca460029f7d53b",
                        "615ad469e27203001dc61019",
                        "6164f55b1ef21c001dd362bf",
                        "6168f7486f412f001e314725",
                        "637ecad9dbd962544ddebded",
                        "637ecb47dbd962c0f8df02cd",
                        "637ecb7cdbd9625a52df3946",
                        "65012fb84cb185847adddb5b",
                    ],
                },
                {"key": "status", "operator": "not_equal_to", "value": "h"},
                {"key": "locationStatus", "operator": "not_in", "value": ["sdc", "h"]},
                {"key": "invalid", "operator": "equal_to", "value": False},
                {"key": "invalidStatus", "operator": "equal_to", "value": ""},
                {"key": "productInvalid", "operator": "equal_to", "value": False},
            ]
        },
        "aggregations": {
            "total": {
                "type": "terms",
                "magicFields": {"id": {"value": "all"}},
                "subAggregations": {"count": {"type": "count"}},
            },
            "revenue": {
                "type": "sum",
                "magicField": {
                    "funcName": "multiply",
                    "fields": ["market.exchangeRate", "revenue"],
                },
            },
            "mktUsers": {
                "filters": [
                    {
                        "key": "mktUserRevenueNotAccepted",
                        "operator": "not_equal_to",
                        "value": True,
                    }
                ],
                "type": "terms",
                "magicFields": {"id": "mktUserId"},
                "subAggregations": {
                    "count": {"type": "count"},
                    "revenue": {
                        "type": "sum",
                        "magicField": {
                            "funcName": "multiply",
                            "fields": ["market.exchangeRate", "revenue"],
                        },
                    },
                },
            },
            "days": {
                "type": "terms",
                "magicFields": {
                    "id": {"funcName": "dateToString", "field": "createdTime"}
                },
                "subAggregations": {
                    "count": {"type": "count"},
                    "revenue": {
                        "type": "sum",
                        "magicField": {
                            "funcName": "multiply",
                            "fields": ["market.exchangeRate", "revenue"],
                        },
                    },
                },
            },
            "mktUserWithDayItems": {
                "filters": [
                    {
                        "key": "mktUserRevenueNotAccepted",
                        "operator": "not_equal_to",
                        "value": True,
                    }
                ],
                "type": "terms",
                "magicFields": {
                    "id": {
                        "funcName": "concat",
                        "fields": [
                            "mktUserId",
                            {"value": "_"},
                            {
                                "funcName": "toString",
                                "field": {
                                    "funcName": "dateToString",
                                    "field": "createdTime",
                                },
                            },
                        ],
                    }
                },
                "subAggregations": {
                    "count": {"type": "count"},
                    "revenue": {
                        "type": "sum",
                        "magicField": {
                            "funcName": "multiply",
                            "fields": ["market.exchangeRate", "revenue"],
                        },
                    },
                },
            },
        },
    }

    url = "https://tizi.asia/core-api/orders/@/statistic?payload={}".format(
        json.dumps(payload, separators=(",", ":"))
    )
    return get_request(url)


def get_items_by_market(market, limit):
    payload = {
        "limit": limit,
        "offset": 0,
        "search": "",
        "orders": {"createdTime": "desc"},
        "filters": [
            {
                "key": "marketId",
                "operator": "equal_to",
                "value": MARKETS[market]["marketId"],
            }
        ],
        "extraParams": {},
        "orderBy": "createdTime",
        "orderType": "desc",
    }

    url = "https://tizi.asia/core-api/orders?payload={}&offset=0&limit={}&orderBy=createdTime&orderType=desc".format(
        json.dumps(payload, separators=(",", ":")), limit
    )
    return get_request(url)


def get_result_item(item, market):
    result = MARKETS[market]["title"]
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
async def get_phi(message):
    status, items = get_items_by_market(PHILIPPIN_MARKET, 5)
    if status is False:
        get_token()
        status, items = get_items_by_market(PHILIPPIN_MARKET, 5)

    if status:
        if items and isinstance(items["items"], list):
            items["items"].reverse()
            for item in items["items"]:
                await reply_message(
                    bot,
                    message,
                    get_result_item(item, PHILIPPIN_MARKET),
                )
        else:
            await reply_message(bot, message, "Item is not list\n")
    else:
        await reply_message(bot, message, items[:300] + "\n")


@bot.message_handler(commands=["malay"])
async def get_malay(message):
    status, items = get_items_by_market(MALAYSIA_MARKET, 5)
    if status is False:
        get_token()
        status, items = get_items_by_market(MALAYSIA_MARKET, 5)

    if status:
        if items and isinstance(items["items"], list):
            items["items"].reverse()
            for item in items["items"]:
                await reply_message(
                    bot,
                    message,
                    get_result_item(item, MALAYSIA_MARKET),
                )
        else:
            await reply_message(bot, message, "Item is not list\n")
    else:
        await reply_message(bot, message, items[:300] + "\n")


@bot.message_handler(commands=["s"])
async def statistic(message):
    local = pytz.timezone(TIME_ZONE)
    now = datetime.now(local)

    status, items = get_list_user()
    if status is False:
        get_token()
        status, items = get_list_user()

    if status:
        if items and isinstance(items["items"], list):
            users = {}
            for user in items["items"]:
                users[user["_id"]] = {
                    "_id": user["_id"],
                    "name": user["name"],
                    "count": 0,
                    "revenue": 0,
                }

            status, statistic = get_statistic(now)
            if status is False:
                get_token()
                status, statistic = get_statistic(now)

            if status:
                if statistic and "mktUsers" in statistic:
                    for k, s in statistic["mktUsers"].items():
                        if k in users:
                            users[k]["count"] = s["info"]["count"]
                            users[k]["revenue"] = s["info"]["revenue"]

            users = sorted(users.values(), key=lambda d: d["revenue"], reverse=True)

            result = "Bảng xếp hạng MKT ngày {}\n".format(
                now.strftime("%d/%m/%Y %H:%M:%S")
            )
            for count, p in enumerate(users):
                if p["count"] > 0:
                    result += "<{}> {}\n ==> Tổng đơn: {} | Tổng tiền {}\n".format(
                        count + 1,
                        p["name"],
                        p["count"],
                        "{:,.0f}".format(round(p["revenue"])),
                    )
            await reply_message(
                bot,
                message,
                result,
            )
        else:
            await reply_message(bot, message, "Item is not list\n")
    else:
        await reply_message(bot, message, "ERROR\n")


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


async def update_new_items(market, notify=True):
    global LIST_ITEM, CHATS, LAST_ITEM_ID
    status, items = get_items_by_market(market, 10)
    if status:
        if items and isinstance(items["items"], list):
            items["items"].reverse()
            for item in items["items"]:
                # LIST_ITEM[item["orderId"]] = item
                if item["orderId"] > LAST_ITEM_ID:
                    LAST_ITEM_ID = item["orderId"]
                    with open(LAST_ITEM_FILE, "w") as f:
                        f.write(LAST_ITEM_ID)
                    for v in CHATS.values():
                        if v["notify"]:
                            await send_message(
                                bot,
                                v["id"],
                                "###########  Đơn hàng mới  ###########\n "
                                + get_result_item(item, market),
                            )


async def periodic():
    global TIME_SLEEP
    while True:
        await update_new_items(PHILIPPIN_MARKET, True)
        await asyncio.sleep(10)
        await update_new_items(MALAYSIA_MARKET, True)
        await asyncio.sleep(TIME_SLEEP)


async def main():
    await asyncio.gather(bot.polling(), periodic())


if __name__ == "__main__":
    get_token()

    print("Get token: {}\n".format(TIZI_TOKEN))

    asyncio.run(main())
