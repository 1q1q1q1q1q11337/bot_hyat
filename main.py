import logging
import traceback
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import telegram

# Импортируем модули
from test_data import TESTS, TOPIC_NAMES
from test_system import *

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = "8553000638:AAF4tg-TYtdSYsbUbDMExI9o2ltETsERwcA"


# Главная клавиатура
def get_main_keyboard():
    keyboard = [
        ["Начало", "Меню"],
        ["Инструкция"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Клавиатура меню
def get_menu_keyboard():
    keyboard = [
        ["01: Оформление корпоративных бронирований"],
        ["02: Изучение основ базовой работы"],
        ["03: Телефонные звонки"],
        ["Дополнительно: тренинги отеля"],
        ["10: Итоги тестирования"],
        ["Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def send_topic_materials(update: Update, context: ContextTypes.DEFAULT_TYPE, topic_number: int):
    """Отправка материалов по теме"""
    topic_name = TOPIC_NAMES.get(topic_number, "Неизвестная тема")

    await update.message.reply_text(
        f"📚 Тема {topic_number}: {topic_name}\n\n"
        "Материалы для изучения:"
    )

    # Для тем 3,4,5,6 отправляем видео
    if topic_number in {3, 4, 5, 6}:
        try:
            # Отправляем видео файл
            video_path = f"materials/topic_{topic_number}_video.mp4"  # Путь к видео файлу
            await update.message.reply_video(
                video=open(video_path, "rb"),
                caption=f"🎥 Видео-материал по теме {topic_number}: {topic_name}"
            )
        except FileNotFoundError:
            await update.message.reply_text(
                f"⚠️ Видео по теме {topic_number} временно недоступно\n"
                f"Тема: {topic_name}\n\n"
                "Обратитесь к администратору для получения материалов."
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка при отправке видео: {str(e)}"
            )
    else:
        # Для остальных тем отправляем документы (как было раньше)
        try:
            file_path = f"materials/topic_{topic_number}.pdf"
            await update.message.reply_document(
                document=open(file_path, "rb"),
                caption=f"📎 Материалы по теме {topic_number}: {topic_name}"
            )
        except FileNotFoundError:
            await update.message.reply_text(
                f"⚠️ Файл по теме {topic_number} временно недоступен\n"
                f"Тема: {topic_name}\n\n"
                "Обратитесь к администратору для получения материалов."
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка при отправке файла: {str(e)}"
            )

    # Кнопка для начала тестирования (для тем, где есть тесты)
    if topic_number in TESTS:
        await update.message.reply_text(
            "После изучения материалов пройдите тестирование:",
            reply_markup=get_test_keyboard(topic_number)
        )


# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    welcome_text = (
        f"Привет, {user.first_name}! 👋\n\n"
        "Добро пожаловать в обучающую систему отдела бронирования!\n"
        "Используйте кнопки для навигации по разделам."
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )


# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if text == "Начало":
        await update.message.reply_text(
            "🎯 Начальная страница\n\n"
            "Здесь вы можете начать работу с обучающей системой.\n"
            "Нажмите 'Меню' для выбора раздела обучения.",
            reply_markup=get_main_keyboard()
        )

    elif text == "Меню":
        await update.message.reply_text(
            "Выберите раздел обучения:",
            reply_markup=get_menu_keyboard()
        )

    elif text == "Инструкция":
        instruction_text = (
            "📖 Инструкция по использованию бота:\n\n"
            "1. 'Начало' - начальная страница\n"
            "2. 'Меню' - открывает разделы обучения\n"
            "3. 'Инструкция' - это руководство\n\n"
            "Для выбора раздела обучения нажмите 'Меню'"
        )
        await update.message.reply_text(
            instruction_text,
            reply_markup=get_main_keyboard()
        )

    elif text == "01: Оформление корпоративных бронирований":
        module_text = (
            "📊 Модуль 1: Оформление корпоративных бронирований\n\n"
            "Темы:\n"
            "1 - Знакомство с основными инструментами работы в OPERA PMS\n"
            "2 - Работа с Outlook, получение доступа к почте отдела бронирования\n"
            "3 - Тренинг: Номерной фонд\n"
            "4 - Тренинг: Корпоративные тарифы\n"
            "5 - Тренинг: Выставление счета в 1С\n"
            "6 - Тренинг: Кредитные линии и постоплата\n"
            "7 - Получение доступа к сервисам Paylink\n"
            "8 - Тренинг: отправление платежной ссылки\n"
            "9 - Получение доступа к 1С, оформление подписи\n\n"
            "Для получения материалов по теме введите номер темы (1-9)"
        )
        await update.message.reply_text(
            module_text,
            reply_markup=get_menu_keyboard()
        )

    elif text == "02: Изучение основ базовой работы":
        module_text = (
            "📧 Модуль 2: Работа с Outlook для отдела бронирования\n\n"
            "В этом модуле вы изучите:\n"
            "• Настройку общего почтового ящика\n"
            "• Отправку писем от имени отдела\n"
            "• Организацию входящей почты\n"
            "• Использование шаблонов и правил\n\n"
            "Для получения материалов введите номер темы (2)"
        )
        await update.message.reply_text(
            module_text,
            reply_markup=get_menu_keyboard()
        )

    elif text == "03: Телефонные звонки":
        module_text = (
            "📞 Модуль 3: Телефонные звонки\n\n"
            "В этом модуле вы изучите:\n"
            "• Техники телефонного этикета\n"
            "• Обработку входящих звонков\n"
            "• Консультирование клиентов\n"
            "• Решение проблем по телефону\n\n"
            "Для получения видео-материалов введите номер темы (3)"
        )
        await update.message.reply_text(
            module_text,
            reply_markup=get_menu_keyboard()
        )

    elif text == "Дополнительно: тренинги отеля":
        module_text = (
            "🏨 Дополнительно: тренинги отеля\n\n"
            "Доступные тренинги:\n"
            "• Стандарты обслуживания\n"
            "• Программа лояльности\n"
            "• Работа с системой управления\n"
            "• Кросс-тренинг с другими отделами\n\n"
            "Для получения материалов обратитесь к менеджеру"
        )
        await update.message.reply_text(
            module_text,
            reply_markup=get_menu_keyboard()
        )

    elif text == "10: Итоги тестирования":
        await show_test_results(update, context)

    elif text in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        topic_number = int(text)
        await send_topic_materials(update, context, topic_number)

    elif text == "Назад":
        await update.message.reply_text(
            "Возврат в главное меню",
            reply_markup=get_main_keyboard()
        )

    # Обработка пароля администратора
    elif context.user_data.get('waiting_for_admin_password'):
        if check_admin_password(text):
            topic_id = context.user_data.get('admin_topic_id', 1)
            reset_attempts(user_id, topic_id)
            await update.message.reply_text(
                "✅ Попытки сброшены! Теперь у вас снова 2 попытки.",
                reply_markup=get_main_keyboard()
            )
            context.user_data['waiting_for_admin_password'] = False
        else:
            await update.message.reply_text(
                "❌ Неверный пароль администратора.",
                reply_markup=get_main_keyboard()
            )
            context.user_data['waiting_for_admin_password'] = False

    else:
        await update.message.reply_text(
            "Я не понимаю эту команду. Пожалуйста, используйте кнопки ниже:",
            reply_markup=get_main_keyboard()
        )


async def show_test_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать результаты тестирования"""
    user_id = update.message.from_user.id
    initialize_user(user_id)

    results_text = "📊 Итоги тестирования\n\n"

    for topic_id, percentage in user_data[user_id]['test_results'].items():
        if topic_id in TOPIC_NAMES:
            topic_name = TOPIC_NAMES[topic_id]
            color = get_color_for_percentage(percentage)
            attempts_used = user_data[user_id]['test_attempts'].get(topic_id, 0)
            attempts_left = 2 - attempts_used

            results_text += f"{color} {topic_name}\n"
            results_text += f"   Результат: {percentage:.1f}%\n"
            results_text += f"   Попыток использовано: {attempts_used}/2\n"
            results_text += f"   Осталось попыток: {attempts_left}\n\n"

    await update.message.reply_text(
        results_text,
        reply_markup=get_menu_keyboard()
    )


# Обработчик нажатий на inline-кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data.startswith("start_test_"):
        topic_id = int(query.data.split("_")[2])

        if can_take_test(user_id, topic_id):
            start_test_session(user_id, topic_id)
            await send_question(update, context, user_id, topic_id, 0)
        else:
            attempts_left = get_attempts_left(user_id, topic_id)
            if attempts_left == 0:
                await query.edit_message_text(
                    f"❌ Вы использовали все 2 попытки для этого теста.\n\n"
                    f"Для сброса попыток введите пароль администратора:",
                    reply_markup=None
                )
                context.user_data['waiting_for_admin_password'] = True
                context.user_data['admin_topic_id'] = topic_id
            else:
                await query.edit_message_text(
                    f"❌ У вас осталось {attempts_left} попыток.",
                    reply_markup=None
                )

    elif query.data.startswith("answer_"):
        parts = query.data.split("_")
        topic_id = int(parts[2])
        question_num = int(parts[3])
        answer = parts[4]

        add_user_answer(user_id, [answer])
        next_question(user_id)

        test_data = TESTS.get(topic_id)
        if test_data and question_num + 1 < len(test_data['questions']):
            await send_question(update, context, user_id, topic_id, question_num + 1)
        else:
            # Завершение теста
            percentage, score, total = calculate_score(user_id, topic_id, test_data)
            color = get_color_for_percentage(percentage)

            result_text = (
                f"🎯 Тест завершен!\n\n"
                f"Тема: {test_data['name']}\n"
                f"Правильных ответов: {score}/{total}\n"
                f"Результат: {color} {percentage:.1f}%\n\n"
            )

            if percentage >= 85:
                result_text += "✅ Отлично! Вы успешно прошли тест!"
            elif percentage >= 50:
                result_text += "⚠️ Хорошо, но есть над чем поработать."
            else:
                result_text += "❌ Необходимо повторить материал."

            await query.edit_message_text(
                result_text,
                reply_markup=None
            )


async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, topic_id: int,
                        question_num: int):
    """Отправить вопрос пользователю"""
    test_data = TESTS.get(topic_id)
    if not test_data or question_num >= len(test_data['questions']):
        return

    question = test_data['questions'][question_num]
    keyboard = get_answer_keyboard(question_num, question['options'], topic_id)

    question_text = f"❓ Вопрос {question_num + 1}/{len(test_data['questions'])}\n\n{question['question']}"

    if hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(question_text, reply_markup=keyboard)
    else:
        await update.message.reply_text(question_text, reply_markup=keyboard)


# Основная функция
# Добавьте эту функцию для обработки ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    error = context.error

    if isinstance(error, telegram.error.TimedOut):
        print(f"Таймаут соединения: {error}")
        # Можно попробовать отправить сообщение пользователю
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Временная проблема с соединением. Пожалуйста, попробуйте еще раз."
                )
        except Exception:
            pass
    else:
        print(f"Произошла ошибка: {error}")


# В основной функции добавьте обработчик ошибок
def main():
    application = (
        Application.builder()
        .token(TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    print("Бот запущен...")
    application.run_polling(
        poll_interval=1.0,
        timeout=30,
        drop_pending_updates=True
    )
if __name__ == "__main__":
    main()