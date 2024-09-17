import asyncio
import difflib
import os
import random
import shutil
from datetime import datetime
from itertools import zip_longest

import gspread
import pandas as pd
import schedule
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from telebot import apihelper
from telebot.async_telebot import AsyncTeleBot

load_dotenv()

client_error = True
client = None

FILE_CHAT_ID = "chat_id.txt"
CHATS = {}

if os.path.exists(FILE_CHAT_ID):
    with open(FILE_CHAT_ID, "r") as f:
        chat_ids = [int(id) for id in f.read().strip().split(",")]
        for id in chat_ids:
            CHATS[id] = {"id": id}

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ID_FILE = os.environ.get("ID_FILE")

apihelper.ENABLE_MIDDLEWARE = True

bot = AsyncTeleBot(BOT_TOKEN)

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


def list_folders_in_directory(directory):
    # Lấy danh sách tất cả các thư mục con trong thư mục được chỉ định
    folders = [f.name for f in os.scandir(directory) if f.is_dir()]
    return folders


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


def save_id_message(message):
    if message.chat.id not in CHATS:
        CHATS[message.chat.id] = {"id": message.chat.id}
        with open(FILE_CHAT_ID, "w") as f:
            f.write(",".join([str(id) for id in CHATS.keys()]))


# # Middleware chạy trước mỗi command
# @bot.middleware_handler(update_types=["message"])
# async def handle_command(bot_instance, message):
#     save_id_message(message)


@bot.message_handler(commands=["l"])
async def get_link(message):
    if message:
        await reply_message(
            bot,
            message,
            "https://docs.google.com/spreadsheets/d/{}/edit?usp=sharing".format(
                ID_FILE
            ),
        )


@bot.message_handler(commands=["r"])
async def run_once(message):
    global client_error
    client_error = False
    init_client()
    await job()
    if message:
        await reply_message(
            bot,
            message,
            "Done",
        )


@bot.message_handler(commands=["c"])
async def get_changes(message):
    global base_dir_data
    times = list_folders_in_directory(base_dir_data)
    times.sort(reverse=True)

    arr = message.text.split()
    try:
        if len(arr) > 1:
            number = int(arr[1])  # Chuyển số thành kiểu integer
        else:
            number = 5
    except Exception as e:
        print(str(e))
        number = 5

    result_str = "Danh sách {} lần thay đổi dữ liệu gần nhất: \n".format(number)

    i = 0
    changes = []

    while number > 0 and i < len(times):
        change_file = os.path.join(base_dir_data, times[i], "change.txt")
        if os.path.exists(change_file):
            changes.append(
                "=========>  {}  <=========\n{}\n".format(
                    datetime.strptime(times[i], "%Y-%m-%d_%H-%M-%S").strftime(
                        "%Y/%m/%d - %H:%M:%S"
                    ),
                    open(change_file, "r", encoding="utf8").read(),
                )
            )
            number -= 1

        i += 1

    changes.reverse()

    for c_str in changes:
        result_str += c_str

    if message:
        await reply_message(
            bot,
            message,
            result_str,
        )


@bot.message_handler(commands=["start", "help"])
async def send_welcome(message):
    save_id_message(message)
    try:
        await bot.reply_to(
            message,
            """
/l      : Lấy link data
/c <n>  : hiển thị n lần thay đổi dữ liệu gần nhất
/r      : Run
""",
        )
    except Exception as e:
        print("!!! Exception occurred")
        print(e)


def init_client():
    global client, client_error
    if client_error:
        # Xác thực Google API
        scope = [
            "https://spreadsheets.google.com/feeds",
            # "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "check-price-2024.json", scope
        )
        client = gspread.authorize(creds)
        client_error = False


def open_by_url(sheet_url):
    global client, client_error
    init_client()
    try:
        spreadsheet = client.open_by_url(sheet_url)
    except Exception as e:
        print(str(e))
        client_error = True
        init_client()
        spreadsheet = client.open_by_url(sheet_url)

    return spreadsheet


# Tải file từ Google Sheet
def download_file():
    global base_dir_data
    # Mở Google Sheet bằng URL
    sheet_url = "https://docs.google.com/spreadsheets/d/{}/edit?usp=sharing".format(
        ID_FILE
    )

    spreadsheet = open_by_url(sheet_url)
    # Lấy tất cả các sheet
    sheets = spreadsheet.worksheets()

    # # Hàm để làm sạch tên sheet
    # def clean_sheet_title(title):
    #     return re.sub(r'[\\/*?:"<>|]', "", title)

    # Đọc dữ liệu từ từng sheet và lưu vào Excel
    folder_path = os.path.join(
        base_dir_data, datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    )
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)

    output_path = os.path.join(folder_path, "price.xlsx")

    with pd.ExcelWriter(output_path) as writer:
        for sheet in sheets:
            data = pd.DataFrame(sheet.get_all_values())
            # Làm sạch tên sheet
            # sheet_name = clean_sheet_title(sheet.title)
            data.to_excel(writer, sheet_name="{}".format(sheet.id), index=False)

    return output_path


def replace_file(current_file, last_file):
    if os.path.exists(last_file):
        os.remove(last_file)

    # Copy file và thay thế
    shutil.copy(current_file, last_file)


# So sánh file mới với file trước đó
async def compare_files_and_repalce(current_file, last_file):
    # Kiểm tra xem file trước đó có tồn tại không
    if not os.path.exists(last_file):
        print("No previous file exists. Saving current file as reference.")
        replace_file(current_file, last_file)
        return

    # Đọc file Excel trước và hiện tại
    previous_data = pd.read_excel(last_file, sheet_name=None)
    current_data = pd.read_excel(current_file, sheet_name=None)
    change_str = ""
    # So sánh nội dung giữa các sheet
    for sheet_name in current_data.keys():
        if sheet_name in previous_data:
            # print(f"\nComparing sheet: {sheet_name}")
            previous_sheet = previous_data[sheet_name]
            current_sheet = current_data[sheet_name]

            # Chuyển đổi các sheet thành danh sách các hàng (dòng)
            previous_rows = previous_sheet.astype(str).values.tolist()
            current_rows = current_sheet.astype(str).values.tolist()

            for i, (prev_row, curr_row) in enumerate(
                zip_longest(previous_rows, current_rows, fillvalue=[""]), start=1
            ):
                diff = list(difflib.unified_diff(prev_row, curr_row, lineterm=""))
                if diff:
                    change_str += "Past: {}\nNew: {}\n\n".format(diff[3], diff[4])

        else:
            change_str += "Sheet mới được thêm vào file\n"
            change_str += "{}\n".format(
                "\n".join([",".join(row) for row in current_rows])
            )

    if change_str:
        print(change_str)
        with open(
            os.path.join(os.path.dirname(current_file), "change.txt"),
            "w",
            encoding="utf8",
        ) as f:
            f.write(change_str)

        for v in CHATS.values():
            await send_message(
                bot,
                v["id"],
                "##### Ồ, có thay đổi nè {} #####\n".format(get_emoji()) + change_str,
            )

    replace_file(current_file, last_file)


# Chạy quy trình tải file và so sánh
async def job():
    global base_dir_data
    print("Checking for updates...")
    current_file = download_file()
    last_file = os.path.join(base_dir_data, "last_price.xlsx")
    await compare_files_and_repalce(current_file, last_file)


# Hàm thực thi pending schedule
async def run_schedule():
    await job()  # Chạy lần đầu ngay lập tức
    # Lập lịch chạy mỗi 2 tiếng
    schedule.every(2).hours.do(job)
    print("Scheduler started. Checking every 2 hours.")
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


# Hàm asyncio chính để chạy cả bot và schedule song song
async def main():
    await asyncio.gather(bot.polling(non_stop=True), run_schedule())


if __name__ == "__main__":
    global base_dir_data
    base_dir_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    asyncio.run(main())
    asyncio.run(main())
