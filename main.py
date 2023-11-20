import asyncio
import logging
from datetime import datetime, timedelta
import re

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.enums.parse_mode import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import config
from db import engine, Base, Session, User, Poll

bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()


class SurveyStates(StatesGroup):
    WaitingForName = State()
    WaitingForDate = State()
    WaitingForInterval = State()


@dp.message(CommandStart())
async def start_handler(msg: Message, state: FSMContext):
    await msg.answer("Привет! Я помогу тебе создавать опросы по расписанию!")
    await state.set_state(SurveyStates.WaitingForName)
    await msg.answer("Придумайте тему опроса.")


@dp.message(SurveyStates.WaitingForName)
async def process_interval_input(msg: types.Message, state: FSMContext):
    chat_id = msg.chat.id
    user_id = msg.from_user.id
    await state.update_data(name=msg.text, user_id=user_id, chat_id=chat_id)
    await msg.answer("Введите дату и время начала опроса в формате YYYY-MM-DD HH:MM")
    await state.set_state(SurveyStates.WaitingForDate)


@dp.message(SurveyStates.WaitingForDate)
async def process_interval_input(msg: types.Message, state: FSMContext):
    await state.update_data(start_date=msg.text)
    await msg.answer("Введите интервал между опросами в минутах:")
    await state.set_state(SurveyStates.WaitingForInterval)


@dp.message(SurveyStates.WaitingForInterval)
async def create_poll(msg: types.Message, state: FSMContext):
    chat_id = msg.chat.id
    data = await state.get_data()

    name = data.get('name')
    start_date_str = data.get('start_date')
    interval_minutes = int(msg.text)

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M")

    scheduler.add_job(scheduled_poll, 'interval', minutes=interval_minutes,
                      start_date=start_date, args=[chat_id, name])
    scheduler.start()

    await state.clear()


@dp.message(Command("stats"))
async def attendance_info(msg: Message):
    # Парсим дату и время из текста сообщения, если они указаны
    date_pattern = re.compile(r"\d{4}-\d{2}-\d{2}")
    match = date_pattern.search(msg.text)

    selected_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if match:
        date_str = match.group()
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    # Парсим время из текста сообщения, если оно указано
    time_pattern = re.compile(r"\d{2}:\d{2}")
    time_match = time_pattern.search(msg.text)

    if time_match:
        time_str = time_match.group()
        selected_time = datetime.strptime(time_str, "%H:%M").time()
        selected_date = datetime.combine(selected_date, selected_time)

    # Получаем опросы, которые проводились в выбранную дату и время
    session = Session()
    polls_on_date = (
        session.query(Poll)
        .filter(
            Poll.date >= selected_date,
            Poll.date < selected_date + timedelta(days=1)
        )
        .all()
    )

    # Для каждого опроса выводим информацию о посещаемости
    for poll in polls_on_date:
        attend_count = (
            session.query(User)
            .filter(User.poll_id == poll.id, User.visits > 0)
            .count()
        )
        absenteeism_count = (
            session.query(User)
            .filter(User.poll_id == poll.id, User.absenteeism > 0)
            .count()
        )

        await msg.answer(
            f"Опрос '{poll.name}' ({poll.date}):\n"
            f"Посетили: {attend_count} человек\n"
            f"Прогуляли: {absenteeism_count} человек"
        )

    session.close()


@dp.message(Command("user_stats"))
async def user_attendance_info(msg: Message):
    # Парсим имя пользователя
    user_name_pattern = re.compile(r"/user_stats\s+(.+)")

    user_name_match = user_name_pattern.search(msg.text)

    if not user_name_match:
        await msg.answer("Неверный формат команды. Используйте /user_stats <b>имя_пользователя</b> <i>дата</i>")
        return

    user_name = user_name_match.group(1)

    # Получаем пользователя и информацию о его посещениях
    session = Session()
    user = session.query(User).filter_by(name=user_name).first()

    if not user:
        await msg.answer(f"Пользователь с именем {user_name} не найден.")
        session.close()
        return

    attend_count = (
        session.query(User)
        .filter(User.poll_id == user.poll_id, User.visits > 0, User.name == user_name)
        .count()
    )
    absenteeism_count = (
        session.query(User)
        .filter(User.poll_id == user.poll_id, User.absenteeism > 0, User.name == user_name)
        .count()
    )

    await msg.answer(
        f"Информация о посещениях пользователя '{user.name}':\n"
        f"Посетил: {attend_count} раз\n"
        f"Прогулял: {absenteeism_count} раз"
    )

    session.close()


@dp.message(Command("stop"))
async def stop_scheduler(msg: Message):
    scheduler.shutdown()
    await msg.answer("VolleyballScheduler остановлен.")


@dp.message(Command('help'))
async def handle_help_command(msg: Message):
    text = (
        "Я бот для создания опросов по расписанию.\n"
        "Сделайте меня администратором, чтобы я мог полноценно работать!\n"
        "Вот список доступных команд:\n"
        "/start - создание опросов по расписанию\n"
        "/stats - получить информацию о посещаемости опросов(/stats <b>время в формате YYYY-MM-DD (HH:MM)</b> (часы и "
        "минуты опциональны))\n"
        "/user_stats - получить информацию о посещениях конкретного пользователя(/user_stats <b>Имя Пользователя</b>)\n"
        "/stop - остановить расписание опросов\n"
        "/help - получить справку о командах"
    )
    await msg.answer(text=text)


@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    selected_option = poll_answer.option_ids[0]
    poll_id = poll_answer.poll_id

    session = Session()

    try:

        user = session.query(User).filter_by(id=user_id, poll_id=poll_id).first()

        if not user:
            new_user_data = {
                'id': user_id,
                'name': poll_answer.user.full_name,
                'absenteeism': 0,
                'visits': 0,
                'poll_id': poll_id
            }

            new_user = User(**new_user_data)
            session.add(new_user)
            session.commit()

            session.query(User).filter_by(id=user_id, poll_id=poll_id).update(update_user_data(selected_option))
            session.query(Poll).filter_by(id=poll_id).update(update_poll_data(selected_option))
            session.commit()

        else:
            session.query(User).filter_by(id=user_id, poll_id=poll_id).update(update_user_data(selected_option))
            session.query(Poll).filter_by(id=poll_id).update(update_poll_data(selected_option))
            session.commit()

    finally:
        session.close()


def update_user_data(option):
    update_data = {}
    if option == 0:
        update_data['visits'] = User.visits + 1
    elif option == 1:
        update_data['absenteeism'] = User.absenteeism + 1
    return update_data


def update_poll_data(option):
    update_data = {}
    if option == 0:
        update_data['attend'] = Poll.attend + 1
    elif option == 1:
        update_data['absent'] = Poll.absent + 1
    return update_data


# Функция, которая будет вызываться по расписанию
async def scheduled_poll(chat_id, poll_name):
    poll_options = ["Иду", "Прогуляю"]
    poll = await bot.send_poll(chat_id=chat_id, question=poll_name, options=poll_options,
                               is_anonymous=False)
    session = Session()

    new_poll_data = {
        'id': poll.poll.id,
        'name': poll_name,
        'absent': 0,
        'attend': 0,
        'date': datetime.now(),
        'chat_id': chat_id
    }

    new_poll = Poll(**new_poll_data)
    session.add(new_poll)
    session.commit()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    Base.metadata.create_all(engine)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
