import asyncio
import re
import random
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os
import json
from dotenv import load_dotenv
import pytz
from keep_alive import keep_alive

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)


months = ["янв", "фев", "март", "апр", "май", "июнь", "июль", "авг", "сент", "окт", "нояб", "дек"]

def load_users_data():
    if not os.path.exists("users.json"):
        with open("users.json", "w") as f:
            json.dump({}, f)
    with open("users.json", "r") as f:
        return json.load(f)

def save_users_data(data):
    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)

def createfont(size):
    return ImageFont.truetype("fonts/Montserrat-Medium.ttf", size=size)

def draw_centered_text(draw, text, y, font, image_width, stroke_width, stroke_fill="white", text_fill="white"):
    y *= 2
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (image_width - text_width) // 2
    if stroke_width:
        for dx in range(-stroke_width * 10 + 8, stroke_width * 10 - 8):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx / 10, y + dy / 10), text, font=font, fill=stroke_fill)
    draw.text((x, y), text, font=font, fill=text_fill)

def draw_text_with_right_padding(draw, text, y, font, right_padding, text_fill="white"):
    y *= 2
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = img.width - text_width - right_padding
    draw.text((x, y), text, font=font, fill=text_fill)

def extract_data_from_message(text):
    ton_amount_match = re.search(r"Стоимость:\s*([\d.]+)\s*TON", text)
    address_match = re.search(r"(?:\n|\r)([A-Z0-9a-z_-]{20,})", text)
    comment_match = re.search(r"(?i)deal\d+", text)

    ton_amount = ton_amount_match.group(1).replace('.', ',') if ton_amount_match else "0,00"
    address_full = address_match.group(1) if address_match else "ADDRUNKNOWN"
    address_short = address_full[:4] + "..." + address_full[-4:]
    comment = comment_match.group(0) if comment_match else "deal0000"

    return ton_amount, address_short, comment

def generate_random_data():
    balance = f"{random.uniform(10, 100):.2f}".replace(".", ",")
    com_ton = f"{random.uniform(0.0033, 0.0035):.9f}"
    com_dollar = f"{float(com_ton) * 3:.3f}"
    com_ton.replace(".", ",")
    com_dollar.replace(".", ",")
    base_tx = list("87d248ce")
    random.shuffle(base_tx)
    transaction = ''.join(base_tx)
    return balance, com_ton, com_dollar, transaction

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.respond("Просто перешлите сообщение сделки гифтпот сюда.")

@bot.on(events.NewMessage(forwards=True))
async def forwarded_message_handler(event):
    text = event.raw_text
    ton_amount, address, comment = extract_data_from_message(text)
    balance, com_ton, com_dollar, transaction = generate_random_data()

    data = {
        'ton_amount': ton_amount,
        'balance': balance,
        'adress': address,
        'comission_ton': com_ton,
        'comission_dollar': com_dollar,
        'comment': comment,
        'transaction': transaction
    }

    await generate_and_send_check(event, data)

global img
async def generate_and_send_check(event, data):
    img_path = "sample-tonkeeper.jpg"
    global img
    img = Image.open(img_path)
    draw = ImageDraw.Draw(img)

    tonamountfont = ImageFont.truetype("fonts/Montserrat-Bold.ttf", size=40)
    semibold = ImageFont.truetype("fonts/Montserrat-SemiBold.ttf", size=26)
    draw_centered_text(draw, "– " + data['ton_amount'] + " TON", 317, tonamountfont, img.width, 1)

    balancefont = createfont(26)
    draw_centered_text(draw, data['balance'] + "$", 345, balancefont, img.width, 0, "white", (136,146,156,255))

    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz)
    formatted_date = f"Отправлено {now.day} {months[now.month - 1]}, {now.strftime('%H:%M')}"
    draw_centered_text(draw, formatted_date, 365, balancefont, img.width, 0, "white", (136,146,156,255))

    draw_text_with_right_padding(draw, data['adress'], 421, semibold, 50)
    draw_text_with_right_padding(draw, data['comission_ton'] + " TON", 465, semibold, 50)
    draw_text_with_right_padding(draw, data['comission_dollar'] + " $", 485, createfont(22), 50, (136,146,156,255))
    draw_text_with_right_padding(draw, data['comment'], 522, semibold, 50)
    draw_text_with_right_padding(draw, data['transaction'], 582.5, ImageFont.truetype("fonts/Montserrat-SemiBold.ttf", size=22), 142, (136,146,156,255))
    draw_text_with_right_padding(draw, data['comment'], 122, createfont(22), 326, (63,67,69,255))

    arial = ImageFont.truetype("fonts/arialmt.ttf", size=21)
    draw.text((22, 15), now.strftime("%H:%M"), font=arial, fill="white")

    path = f"result_{event.sender_id}.jpg"
    img.save(path)

    await event.respond("Ваш чек готов:", file=path)
    os.remove(path)

    users_data = load_users_data()
    user_id = str(event.sender_id)
    if user_id in users_data:
        users_data[user_id]['checks_created'] += 1
        save_users_data(users_data)

if __name__ == '__main__':
    keep_alive()
    print("Бот запущен...")
    bot.run_until_disconnected()
