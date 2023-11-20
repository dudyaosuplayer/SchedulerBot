from pyrogram import Client
from pyrogram.types import ChatMember


import config
from db import Session, users

api_id = '6489717828'
# api_hash = config.API_HASH
bot_token = config.BOT_TOKEN

app = Client("my_account", api_id=api_id, bot_token=bot_token)


async def add_users_to_database(chat_id):
    async with app:
        # Добавляем участников в базу данных
        session = Session()
        async for member in app.get_chat_members(chat_id):
            if member.user:
                user_data = {
                    'id': member.user.id,
                    'name': member.user.first_name,  # Или другое поле с именем пользователя
                    'absenteeism': 0,
                    'visits': 0
                }
                user = users(**user_data)
                session.add(user)

        session.commit()

# from aiogram import types, F, Router
# from aiogram.types import Message
# from aiogram.filters import Command
#
# router = Router()
#
#
# @router.message(Command("start"))
# async def start_handler(msg: Message):
#     await msg.answer("Привет! Я помогу тебе создавать опросы!")
#
#
# @router.message(Command('help'))
# async def handle_help_command(msg: Message):
#     text = 'Я бот для опросов. Вы можете использовать следующие команды:\n' \
#            '/create_poll - Создать новый опрос\n' \
#            '/close_poll - Закрыть активный опрос\n' \
#            '/get_stats - Получить статистику опроса'
#     await msg.answer(text=text)
#
#
# @router.message()
# async def message_handler(msg: Message):
#     await msg.answer(f"Твой ID: {msg.from_user.id}")
