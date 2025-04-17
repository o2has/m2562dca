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
import photo_edit

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

get_percents = False
data = None
waiting_for_image = {}
user_states = {}

months = ["янв", "фев", "март", "апр", "май", "июнь", "июль", "авг", "сент", "окт", "нояб", "дек"]
percents = 50

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
    com_ton = com_ton.replace(".", ",")
    com_dollar = com_dollar.replace(".", ",")
    base_tx = list("87d248ce")
    random.shuffle(base_tx)
    transaction = ''.join(base_tx)
    return balance, com_ton, com_dollar, transaction
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user = await event.get_sender()
    users_data = load_users_data()
    user_id = str(user.id)

    is_new_user = user_id not in users_data
    if is_new_user:
        users_data[user_id] = {
            "username": user.username or "без username",
            "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
            "checks_created": 0
        }
        save_users_data(users_data)

        message_for_admin = (
            f"👤 Новый пользователь запустил бота:\n"
            f"Имя: {users_data[user_id]['full_name']}\n"
            f"Username: @{users_data[user_id]['username']}\n"
            f"ID: {user_id}"
        )
        try:
            await bot.send_message(ADMIN_ID, message_for_admin)
        except Exception as e:
            print(f"Не удалось отправить сообщение админу: {e}")

    await event.respond(
        "Выберите систему:",
        buttons=[Button.inline("Tonkeeper", b"tonkeeper")]
    )

@bot.on(events.CallbackQuery(data=b"tonkeeper"))
async def tonkeeper_handler(event):
    user_id = event.sender_id
    user_states[user_id] = {'step': 'choose_method', 'data': {}}
    await event.respond(
        "Как вы хотите создать чек?",
        buttons=[
            [Button.inline("Ввести данные вручную", b"manual_input")],
            [Button.inline("Переслать сообщение Giftpot", b"forward_message")]
        ]
    )
    
@bot.on(events.CallbackQuery(data=b"manual_input"))
async def manual_input_handler(event):
    user_id = event.sender_id
    user_states[user_id] = {'step': 'ton_amount', 'data': {}}
    await event.respond("Введите количество отправленных тонов:")

@bot.on(events.CallbackQuery(data=b"forward_message"))
async def forward_message_handler(event):
    await event.respond("Просто перешлите сообщение сделки гифтпот сюда.")

@bot.on(events.NewMessage(forwards=True))
async def forwarded_message_handler(event):
    global data, get_percents
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

    await event.respond("Введите количество процентов на скрине: ")
    get_percents = True

@bot.on(events.NewMessage)
async def message_handler(event):
    global get_percents, percents
    
    if get_percents and not event.forward:
        percents = event.raw_text
        get_percents = False
        await generate_and_send_check(event, data, percents)
        return
    
    user_id = event.sender_id
    if user_id not in user_states:
        return

    state = user_states[user_id]
    step = state['step']
    text = event.raw_text.strip()

    state['data'][step] = text

    next_steps = {
        'ton_amount': ('balance', "Введите ваш баланс (в долларах):"),
        'balance': ('adress', "Введите адрес получателя (4 символа...4 символа):"),
        'adress': ('comission_ton', "Введите комиссию в тонах:"),
        'comission_ton': ('comission_dollar', "Введите комиссию в долларах:"),
        'comission_dollar': ('comment', "Введите комментарий:"),
        'comment': ('transaction', "Введите ID транзакции (например (25d91dca)):"),
        'transaction': ('percents', "Введите количество процентов на скрине:"),
    }

    if step in next_steps:
        next_step, prompt = next_steps[step]
        state['step'] = next_step
        await event.respond(prompt)
    elif step == 'percents':
        percents = text
        await generate_and_send_check(event, state['data'], text)   
        del user_states[user_id]

global img
async def generate_and_send_check(event, data, percents=None):
    img_path = "images/sample-tonkeeper.png"
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

    draw.text((32, 9), now.strftime("%H:%M"), font=ImageFont.truetype("fonts/SamsungSans-Regular.ttf", size=22), fill="white")
    
    percent_pos = (502, 9) if int(percents) >= 10 else (512, 9)
    draw.text(percent_pos, percents + "%", font=ImageFont.truetype("fonts/SamsungSans-Regular.ttf", size=22), fill="white")
    color = "white" if int(percents) >= 15 else "#e3511c"
    draw.rectangle(
        [(550, 28 - int(int(percents) / 100 * 11)), (559, 28)],
        fill=color
    )

    path = f"result_{event.sender_id}.jpg"
    img.save(path)

    buttons = None
    if percents:
        buttons = [Button.inline("Сделать скрин мультизадачности", b"multitask")]

    await event.respond("Ваш чек готов:", file=path, buttons=buttons)
    os.remove(path)

    users_data = load_users_data()
    user_id = str(event.sender_id)
    if user_id in users_data:
        users_data[user_id]['checks_created'] += 1
        save_users_data(users_data)

@bot.on(events.CallbackQuery(data=b"multitask"))
async def on_multitask_button(event):
    user_id = str(event.sender_id)
    waiting_for_image[user_id] = True
    await event.respond("Пожалуйста, отправьте второй скрин для многозадачности.")

@bot.on(events.NewMessage(func=lambda e: e.photo))
async def handle_photo(event):
    user_id = str(event.sender_id)
    if waiting_for_image.get(user_id):
        waiting_for_image[user_id] = False

        photo = await event.download_media()
        multitask_path = f"images/screenshots/temp_{user_id}.jpg"
        os.rename(photo, multitask_path)
        second_screen = Image.open(multitask_path)
        await generate_multitask_screen(event, second_screen)
        os.remove(multitask_path)

async def generate_multitask_screen(event, second_screen):
    global img, percents
    
    base = Image.open("images/sample-multitask.png")
    img = photo_edit.crop_image_top_bottom(img, 73)
    img = photo_edit.resize_image(img, 40)
    img = photo_edit.round_corners(img, 23)

    base.paste(img, (117, 204), img)
    img = base
    
    logo = Image.open("images/tonkeeper-logo.png")
    logo = photo_edit.resize_image(logo, 76.5)
    img.paste(logo, (224, 152), logo)
    
    second_screen = photo_edit.crop_image_top_bottom(second_screen, 73)
    second_screen = photo_edit.resize_image(second_screen, 40)
    second_screen = photo_edit.round_corners(second_screen, 23)
    second_screen = photo_edit.resize_image(second_screen, 13.4)
    
    img.paste(second_screen, (-220, 249), second_screen)
    
    draw = ImageDraw.Draw(img)
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz)
    draw.text((32, 9), now.strftime("%H:%M"), font=ImageFont.truetype("fonts/SamsungSans-Regular.ttf", size=22), fill="white")
    percent_pos = (502, 9) if int(percents) >= 10 else (512, 9)
    draw.text(percent_pos, str(percents) + "%", font=ImageFont.truetype("fonts/SamsungSans-Regular.ttf", size=22), fill="white")
    color = "white" if int(percents) >= 15 else "#e3511c"
    draw.rectangle(
        [(550, 30 - int(int(percents) / 100 * 11)), (558, 30)],
        fill=color
    )

    path = f"result_{event.sender_id}.png"
    base.save(path)
    await event.reply(file=path)
    os.remove(path)

if __name__ == '__main__':
    print("Бот запущен...")
    bot.run_until_disconnected()
