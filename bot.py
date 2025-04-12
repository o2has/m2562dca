import asyncio
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os
import json
from dotenv import load_dotenv
import pytz

# Конфигурация
# BOT_TOKEN = os.getenv('BOT_TOKEN')
# API_ID = int(os.getenv('API_ID'))
# API_HASH = os.getenv('API_HASH')
# ADMIN_ID = int(os.getenv('ADMIN_ID'))

BOT_TOKEN = '8094482415:AAGw1SYEkXDNO5gLo1aqo5I04gAuNzveSa8'
API_ID = 22065196
API_HASH = '035da06d12ecf7f788dc59b5af91fac0'
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
ADMIN_ID = 5673842371

# Состояния пользователя
user_states = {}

months = [
    "янв", "фев", "март", "апр", "май", "июнь",
    "июль", "авг", "сент", "окт", "нояб", "дек"
]

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

        # Уведомляем админа
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
        # Стартовое сообщение пользователю
    user_states[event.sender_id] = {'step': 'choose_system', 'data': {}}
    await event.respond(
        "Привет! Какой чек нам нужен? Выберите систему:",
        buttons=[Button.inline("Tonkeeper", b"tonkeeper")]
    )

@bot.on(events.CallbackQuery(data=b"tonkeeper"))
async def tonkeeper_handler(event):
    user_id = event.sender_id
    user_states[user_id] = {'step': 'ton_amount', 'data': {}}
    await event.respond("Введите количество отправленных тонов:")

@bot.on(events.NewMessage)
async def handle_messages(event):
    user_id = event.sender_id
    if user_id not in user_states:
        return

    state = user_states[user_id]
    step = state['step']
    text = event.text.strip()

    state['data'][step] = text

    next_steps = {
        'ton_amount': ('balance', "Введите ваш баланс (в долларах):"),
        'balance': ('adress', "Введите адрес получателя (4 символа...4 символа):"),
        'adress': ('comission_ton', "Введите комиссию в тонах:"),
        'comission_ton': ('comission_dollar', "Введите комиссию в долларах:"),
        'comission_dollar': ('comment', "Введите комментарий:"),
        'comment': ('transaction', "Введите ID транзакции (например (25d91dca)):"),
    }

    if step in next_steps:
        next_step, prompt = next_steps[step]
        state['step'] = next_step
        await event.respond(prompt)
    elif step == 'transaction':
        await generate_and_send_check(event, state['data'])
        del user_states[user_id]

async def generate_and_send_check(event, data):
    global img
    img = Image.open("sample-tonkeeper.jpg")
    draw = ImageDraw.Draw(img)

    tonamountfont = ImageFont.truetype("fonts/Montserrat-Bold.ttf", size=36)
    semibold = ImageFont.truetype("fonts/Montserrat-SemiBold.ttf", size=26)
    draw_centered_text(draw, "– " + data['ton_amount'] + " TON", 320, tonamountfont, img.width, 1)

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
    draw_text_with_right_padding(draw, data['comment'], 121, createfont(22), 329, (63,67,69,255))

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
    print("Бот запущен...")
    bot.run_until_disconnected()
