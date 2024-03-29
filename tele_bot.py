import asyncio
import json
import os
import random
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
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
        "last_item_file": "last_item_phi.txt",
        "last_item_id": "",
    },
    MALAYSIA_MARKET: {
        "marketId": "60e71da9563671002b12177f",
        "title": "Đơn hàng thị trường: Malay\n",
        "last_item_file": "last_item_malay.txt",
        "last_item_id": "",
    },
}
MYID = "633e83202837f9a4282e44ab"

TIZI_TOKEN = None
LIST_ITEM = {}

for market in MARKETS.values():
    if os.path.exists(market["last_item_file"]):
        with open(market["last_item_file"], "r") as f:
            market["last_item_id"] = f.read().strip()

FILE_CHAT_ID = "chat_id.txt"
# CHATS = {5496851372: {"id": 5496851372, "notify": True}}
CHATS = {}

if os.path.exists(FILE_CHAT_ID):
    with open(FILE_CHAT_ID, "r") as f:
        chat_ids = [int(id) for id in f.read().strip().split(",")]
        for id in chat_ids:
            CHATS[id] = {"id": id, "notify": True}

EMOJIS = {}
FILE_EMOJI = "asciimoji.txt"
if os.path.exists(FILE_EMOJI):
    with open("asciimoji.txt", "r", encoding="utf8") as f:
        EMOJIS = f.readlines()
        EMOJIS = dict([e.strip().split(" ", 1) for e in EMOJIS])


def get_emoji():
    global EMOJIS
    if EMOJIS:
        word, emoji = random.choice(list(EMOJIS.items()))
        return emoji
        # return "{} ({})".format(emoji, word)

    # return "{} ({})".format("＼(＾O＾)／", "woo")
    return "＼(＾O＾)／"


os.makedirs(os.path.dirname("logs/"), exist_ok=True)

TIME_SLEEP = int(os.environ.get("TIME_SLEEP", 180))

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


@bot.message_handler(commands=["id"])
async def my_id(message):
    print(message.from_user.id)
    try:
        await bot.reply_to(message, str(message.from_user.id))
    except Exception as e:
        print("!!! Exception occurred")
        print(e)


async def update_file_chat_id():
    with open(FILE_CHAT_ID, "w") as f:
        f.write(",".join([str(id) for id in CHATS.keys()]))


@bot.message_handler(commands=["on"])
async def turn_on_auto(message):
    if message.chat.id not in CHATS:
        CHATS[message.chat.id] = {"id": message.chat.id, "notify": True}
        await update_file_chat_id()
    else:
        CHATS[message.chat.id]["notify"] = True
    try:
        await bot.reply_to(message, "Turned on notification automatically!\n")
    except Exception as e:
        print("!!! Exception occurred")
        print(e)


@bot.message_handler(commands=["off"])
async def turn_off_auto(message):
    if message.chat.id in CHATS:
        CHATS[message.chat.id]["notify"] = False
    try:
        await bot.reply_to(message, "Turned off notification!\n")
    except Exception as e:
        print("!!! Exception occurred")
        print(e)


@bot.message_handler(commands=["status"])
async def get_status(message):
    try:
        await bot.reply_to(
            message,
            "Notification: {}\n".format("On" if message.chat.id in CHATS else "Off"),
        )
    except Exception as e:
        print("!!! Exception occurred")
        print(e)


def process_date(t):
    global TIME_ZONE
    local = pytz.timezone(TIME_ZONE)
    naive = datetime.fromtimestamp(t / 1000.0, local)
    return naive.strftime("%d/%m/%Y %H:%M:%S")


async def reply_message(bot, message, result):
    try:
        if len(result) > 4095:
            for x in range(0, len(result), 4095):
                await bot.reply_to(message, text=result[x : x + 4095])
        else:
            await bot.reply_to(message, text=result)
    except Exception as e:
        print("!!! Exception occurred")
        print(e)


async def send_message(bot, chat_id, result):
    try:
        if len(result) > 4095:
            for x in range(0, len(result), 4095):
                await bot.send_message(chat_id, text=result[x : x + 4095])
        else:
            await bot.send_message(chat_id, text=result)
    except Exception as e:
        print("!!! Exception occurred")
        print(e)


def get_request(url):
    try:
        response = requests.request("GET", url, headers=get_headers(TIZI_TOKEN))
        if response.ok:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        print("!!! Exception occurred {}".format(url))
        print(e)
        return False, "Exception occurred {}".format(url)


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
    global MARKETS
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
    result += "Tên sản phẩm: {} \n".format(
        item["productCombo"]["name"] if item["productCombo"] else ""
    )
    result += "Tên mkt: {} \n".format(item["orderRequest"]["combo"])
    result += "Tổng giá: {} \n".format(
        item["productCombo"]["localPrice"] if item["productCombo"] else 0
    )
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


async def get_market(message, market):
    status, items = get_items_by_market(market, 5)
    if status is False:
        get_token()
        status, items = get_items_by_market(market, 5)

    if status:
        if items and isinstance(items["items"], list):
            items["items"].reverse()
            for item in items["items"][-5:]:
                await reply_message(
                    bot,
                    message,
                    get_result_item(item, market),
                )
        else:
            await reply_message(bot, message, "Item is not list\n")
    else:
        await reply_message(bot, message, items[:300] + "\n")


async def stat_by_date(message, market, day):
    status, items = get_items_by_market(market, 50)
    if status is False:
        get_token()
        status, items = get_items_by_market(market, 50)

    start_day_timestamp = int(
        day.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000
    )

    end_day_timestamp = int(
        day.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp()
        * 1000
    )

    item_stats = {}

    others = []

    if status:
        if items and isinstance(items["items"], list):
            items["items"].reverse()

            for item in items["items"]:
                if (
                    item["createdTime"] >= start_day_timestamp
                    and item["createdTime"] <= end_day_timestamp
                ):
                    if item["orderRequest"]["utm_medium"]:
                        if item["orderRequest"]["utm_medium"] not in item_stats:
                            item_stats[item["orderRequest"]["utm_medium"]] = {
                                "active": 0,
                                "singleton": 0,
                            }
                        if item["status"]:
                            item_stats[item["orderRequest"]["utm_medium"]][
                                "singleton"
                            ] += 1
                        else:
                            item_stats[item["orderRequest"]["utm_medium"]][
                                "active"
                            ] += 1
                    else:
                        others.append(
                            {
                                "name": item["orderRequest"]["combo"],
                                "time": process_date(item["createdTime"]),
                                "status": item["status"],
                            }
                        )

            result = "Thống kê số đơn theo ads thị trường {} ngày {}\n".format(
                market, day.strftime("%d/%m/%Y")
            )
            utms = sorted(item_stats.keys())
            for utm in utms:
                result += "=> {} |====| Đơn sống: {} | Đơn trùng: {}\n".format(
                    utm, item_stats[utm]["active"], item_stats[utm]["singleton"]
                )
            result += "=> {} = {}\n".format("Không xác định", len(others))

            if len(others) > 0:
                for item in others:
                    result += "        - {} | {} {}\n".format(
                        item["name"],
                        item["time"],
                        "| Trạng thái: HỦY" if item["status"] else "",
                    )

            await reply_message(
                bot,
                message,
                result,
            )
        else:
            await reply_message(bot, message, "Item is not list\n")
    else:
        await reply_message(bot, message, items[:300] + "\n")


def extract_arg(arg):
    return arg.split(" ", 1)[1:]


async def get_search(message, market, day):
    text_search = extract_arg(message.text)
    if len(text_search) == 0:
        await reply_message(bot, message, "Thiếu từ khóa tìm kiếm\n")
        return
    else:
        text_search = text_search[0].strip().lower()
    status, items = get_items_by_market(market, 50)
    if status is False:
        get_token()
        status, items = get_items_by_market(market, 50)

    start_day_timestamp = int(
        day.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000
    )

    end_day_timestamp = int(
        day.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp()
        * 1000
    )

    item_stats = []

    if status:
        if items and isinstance(items["items"], list):
            items["items"].reverse()

            for item in items["items"]:
                if (
                    item["createdTime"] >= start_day_timestamp
                    and item["createdTime"] <= end_day_timestamp
                ):
                    if (
                        item["orderRequest"]["utm_medium"]
                        and text_search in item["orderRequest"]["utm_medium"].lower()
                    ):
                        item_stats.append(item)

            await reply_message(
                bot,
                message,
                'Có {} đơn hàng thị trường {} khớp với từ khóa "{}" ngày {}\n'.format(
                    len(item_stats),
                    market.upper(),
                    text_search,
                    day.strftime("%d/%m/%Y"),
                ),
            )
            for item in item_stats:
                await reply_message(
                    bot,
                    message,
                    get_result_item(item, market),
                )
        else:
            await reply_message(bot, message, "Item is not list\n")
    else:
        await reply_message(bot, message, items[:300] + "\n")


@bot.message_handler(commands=["phi"])
async def get_phi(message):
    await get_market(message, "phi")


@bot.message_handler(commands=["malay"])
async def get_malay(message):
    await get_market(message, "malay")


@bot.message_handler(commands=["t"])
async def get_today(message):
    local = pytz.timezone(TIME_ZONE)
    now = datetime.now(local)
    await stat_by_date(message, PHILIPPIN_MARKET, now)
    await stat_by_date(message, MALAYSIA_MARKET, now)


@bot.message_handler(commands=["y"])
async def get_yesterday(message):
    local = pytz.timezone(TIME_ZONE)
    now = datetime.now(local)
    yesterday = now - timedelta(1)
    await stat_by_date(message, PHILIPPIN_MARKET, yesterday)
    await stat_by_date(message, MALAYSIA_MARKET, yesterday)


async def process_statistic(message=None):
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

            result = "Bảng xếp hạng MKT ngày {}\n".format(now.strftime("%d/%m/%Y"))
            for count, p in enumerate(users):
                if p["count"] > 0:
                    result += "<{}> {}\n ==> Tổng đơn: {} | Tổng tiền {}\n".format(
                        count + 1,
                        p["name"],
                        p["count"],
                        "{:,.0f}".format(round(p["revenue"])),
                    )

                    file_name = "logs/{}/{}.txt".format(
                        now.strftime("%Y-%m-%d"), p["_id"]
                    )
                    os.makedirs(os.path.dirname(file_name), exist_ok=True)
                    with open(file_name, "a") as stat_f:
                        stat_f.write(
                            "{} {} {}\n".format(
                                now.strftime("%H:%M:%S"),
                                p["count"],
                                p["revenue"],
                            )
                        )

            if message:
                await reply_message(
                    bot,
                    message,
                    result,
                )
        else:
            if message:
                await reply_message(bot, message, "Item is not list\n")
    else:
        if message:
            await reply_message(bot, message, "ERROR\n")


@bot.message_handler(commands=["s"])
async def statistic(message):
    await process_statistic(message=message)


@bot.message_handler(commands=["start", "help"])
async def send_welcome(message):
    try:
        await bot.reply_to(
            message,
            """
/start, /help  : Xem danh sách tính năng bot cung cấp
/on     : Bật tự động thông báo khi có đơn hàng mới
/off    : Tắt tự động thông báo khi có đơn hàng mới
/status : Xem trạng thái bật tắt tự động thông báo
/search [chuỗi tìm kiếm] : Tìm những đơn hàng trong ngày khớp với chuỗi tìm kiếm 
/s      : Thống kê doanh số trong ngày
/t      : Thống kê số đơn theo ads hôm nay
/y      : Thống kê số đơn theo ads hôm qua
/d      : Vẽ biểu đồ             
/phi    : Xem 5 đơn hàng gần nhất thị trường Philippin
/malay  : Xem 5 đơn hàng gần nhất thị trường Malaysia
/id     : Lấy ID người dùng Telegram
""",
        )
    except Exception as e:
        print("!!! Exception occurred")
        print(e)


@bot.message_handler(commands=["search"])
async def search(message):
    local = pytz.timezone(TIME_ZONE)
    now = datetime.now(local)

    await get_search(message, PHILIPPIN_MARKET, now)
    await get_search(message, MALAYSIA_MARKET, now)


async def draw_process(message, now, users):
    day_str = now.strftime("%Y-%m-%d")
    # day_str = "2023-11-11"
    folder = "logs/"
    FJoin = os.path.join

    path = FJoin(os.path.abspath(folder), day_str)

    fig, ax = plt.subplots(figsize=(12, 10), layout="constrained")
    les = []
    data = []
    for file in os.listdir(path):
        id = file.strip().split(".")[0]
        with open(FJoin(path, file)) as f:
            times = []
            counts = []
            revenues = []
            for line in f.readlines():
                arr = line.strip().split(" ")
                if len(arr) == 3:
                    times.append(
                        datetime.strptime(
                            "{} {}".format(day_str, arr[0]), "%Y-%m-%d %H:%M:%S"
                        )
                    )
                    counts.append(int(arr[1]))
                    revenues.append(float(arr[2]))

        data.append(
            {
                "id": id,
                "name": users[id]["name"].split("-")[0].strip(),
                "times": times,
                "counts": counts,
                "revenues": revenues,
                "count": max(counts),
                "revenue": max(revenues),
            }
        )

    data = sorted(data, key=lambda x: x["revenue"], reverse=True)
    for i, item in enumerate(data):
        (le,) = ax.plot(
            item["times"],
            item["counts"],
            label="{} - {} | {} | {}".format(
                i + 1,
                item["name"],
                item["count"],
                "{:,.0f}".format(round(item["revenue"])),
            ),
        )
        les.append(le)

    ax.legend(handles=les)

    # Giving title to the chart using plt.title
    plt.title("Số đơn theo thời gian")

    # rotating the x-axis tick labels at 30degree
    # towards right
    plt.xticks(rotation=30, ha="right")

    # Providing x and y label to the chart
    plt.xlabel("Date {}".format(day_str))
    plt.ylabel("Thời gian")
    plt.savefig("test.png")
    try:
        await bot.send_photo(message.chat.id, open("test.png", "rb"))
    except Exception as e:
        print("!!! Exception occurred")
        print(e)

    # bot.clean_tmp_dir()


@bot.message_handler(commands=["d"])
async def draw(message):
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
            await draw_process(message, now, users)
        else:
            if message:
                await reply_message(bot, message, "Item is not list\n")
    else:
        if message:
            await reply_message(bot, message, "ERROR\n")


async def update_new_items(market, notify=True):
    global LIST_ITEM, CHATS, MARKETS
    status, items = get_items_by_market(market, 10)
    if status:
        if items and isinstance(items["items"], list):
            items["items"].reverse()
            for item in items["items"]:
                # LIST_ITEM[item["orderId"]] = item
                if item["orderId"] > MARKETS[market]["last_item_id"]:
                    MARKETS[market]["last_item_id"] = item["orderId"]
                    with open(MARKETS[market]["last_item_file"], "w") as f:
                        f.write(MARKETS[market]["last_item_id"])
                    for v in CHATS.values():
                        if v["notify"]:
                            await send_message(
                                bot,
                                v["id"],
                                "##### Ồ, có đơn {} #####\n{}".format(
                                    get_emoji(),
                                    "(-_-) Cơ mà trùng mất rồi\n"
                                    if item["customerRefusedStatus"]
                                    else "",
                                )
                                + get_result_item(item, market),
                            )


async def periodic():
    global TIME_SLEEP
    while True:
        await update_new_items(PHILIPPIN_MARKET, True)
        await asyncio.sleep(10)
        await update_new_items(MALAYSIA_MARKET, True)
        await asyncio.sleep(10)
        await process_statistic(message=None)
        await asyncio.sleep(TIME_SLEEP)


async def main():
    await asyncio.gather(bot.polling(), periodic())


if __name__ == "__main__":
    get_token()

    print("Get token: {}\n".format(TIZI_TOKEN))

    asyncio.run(main())
