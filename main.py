import logging
import traceback
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import telegram

# Импортируем модули
from test_data import TESTS, TOPIC_NAMES
from test_system import *
from final_test_data import *
from data_storage import get_all_test_results, get_all_final_results

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
TOKEN = "8553000638:AAF4tg-TYtdSYsbUbDMExI9o2ltETsERwcA"

# Словарь для хранения задач таймеров
timer_tasks = {}

# Главная клавиатура
def get_main_keyboard():
    keyboard = [
        ["Начало", "Меню"],
        ["Инструкция", "Админ-панель"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Клавиатура меню
def get_menu_keyboard():
    keyboard = [
        ["01: Оформление корпоративных бронирований"],
        ["02: Изучение основ базовой работы"],
        ["03: Телефонные звонки"],
        ["Дополнительно: тренинги отеля"],
        ["🎯 Итоговый тест"],
        ["10: Итоги тестирования"],
        ["Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Клавиатура админа
def get_admin_keyboard():
    keyboard = [
        ["📊 Получить отчет", "📋 Отчет по итоговому тесту"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_final_test_keyboard(question_num):
    """Клавиатура для финального теста"""
    from final_test_data import FINAL_TEST

    keyboard = []
    question = FINAL_TEST['questions'][question_num]

    for i, option in enumerate(question['options']):
        letter = chr(97 + i)  # a, b, c, d
        keyboard.append([telegram.InlineKeyboardButton(
            option,
            callback_data=f"final_answer_{question_num}_{i}_{letter}"
        )])

    # Кнопка для завершения теста досрочно
    if question_num > 0:
        keyboard.append([telegram.InlineKeyboardButton(
            "🏁 Завершить тест досрочно",
            callback_data=f"final_finish"
        )])

    return telegram.InlineKeyboardMarkup(keyboard)

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
            video_path = f"materials/topic_{topic_number}_video.mp4"
            if os.path.exists(video_path):
                await update.message.reply_video(
                    video=open(video_path, "rb"),
                    caption=f"🎥 Видео-материал по теме {topic_number}: {topic_name}"
                )
            else:
                await update.message.reply_text(
                    f"⚠️ Видео по теме {topic_number} временно недоступно"
                )
        except Exception as e:
            logging.error(f"Ошибка отправки видео: {e}")
    else:
        try:
            file_path = f"materials/topic_{topic_number}.pdf"
            if os.path.exists(file_path):
                await update.message.reply_document(
                    document=open(file_path, "rb"),
                    caption=f"📎 Материалы по теме {topic_number}: {topic_name}"
                )
            else:
                await update.message.reply_text(
                    f"⚠️ Файл по теме {topic_number} временно недоступен"
                )
        except Exception as e:
            logging.error(f"Ошибка отправки файла: {e}")

    # Кнопка для начала тестирования
    if topic_number in TESTS:
        await update.message.reply_text(
            "После изучения материалов пройдите тестирование:",
            reply_markup=get_test_keyboard(topic_number)
        )


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

    # Проверка на ожидание ввода ФИО
    if context.user_data.get('waiting_for_fio'):
        if text.strip():
            fio = text.strip()
            topic_id = context.user_data.get('pending_test_id')

            if topic_id:
                # Проверяем историю тестирования
                history = get_user_test_history(fio, topic_id)

                if not history['exists']:
                    # Новый пользователь
                    await update.message.reply_text(
                        f"✅ Добро пожаловать, {fio}!\n\n"
                        "Вы можете начать тестирование:",
                        reply_markup=get_test_keyboard(topic_id)
                    )
                    context.user_data['current_fio'] = fio

                elif history['attempts'] == 0:
                    # Пользователь есть, но тест не проходил
                    await update.message.reply_text(
                        f"✅ С возвращением, {fio}!\n\n"
                        "Вы можете начать тестирование:",
                        reply_markup=get_test_keyboard(topic_id)
                    )
                    context.user_data['current_fio'] = fio

                elif history['attempts'] == 1:
                    # Одна попытка использована
                    await update.message.reply_text(
                        f"✅ С возвращением, {fio}!\n\n"
                        f"📊 Ваш предыдущий результат: {history['percentage']:.1f}%\n"
                        f"📝 Использовано попыток: {history['attempts']}/2\n\n"
                        "У вас осталась 1 попытка. Вы можете начать тестирование:",
                        reply_markup=get_test_keyboard(topic_id)
                    )
                    context.user_data['current_fio'] = fio

                elif history['attempts'] >= 2:
                    # Все попытки использованы
                    await update.message.reply_text(
                        f"❌ {fio}, вы использовали все 2 попытки для этого теста.\n\n"
                        f"📊 Ваш лучший результат: {history['percentage']:.1f}%\n\n"
                        "Для сброса попыток введите пароль администратора:"
                    )
                    context.user_data['waiting_for_admin_password'] = True
                    context.user_data['admin_topic_id'] = topic_id
                    context.user_data['admin_fio'] = fio
                else:
                    await update.message.reply_text(
                        f"✅ ФИО сохранено: {fio}\n\n"
                        "Вы можете начать тестирование:",
                        reply_markup=get_test_keyboard(topic_id)
                    )
                    context.user_data['current_fio'] = fio
            else:
                await update.message.reply_text(
                    f"✅ ФИО сохранено: {fio}\n\n"
                    "Теперь вы можете выбрать тест из меню.",
                    reply_markup=get_main_keyboard()
                )
                context.user_data['current_fio'] = fio

            # Очищаем временные данные
            context.user_data['waiting_for_fio'] = False
            context.user_data.pop('pending_test_id', None)

        else:
            await update.message.reply_text("❌ Пожалуйста, введите корректные ФИО.")
        return

    # Проверка на ожидание пароля администратора для сброса попыток
    elif context.user_data.get('waiting_for_admin_password'):
        if check_admin_password(text):
            topic_id = context.user_data.get('admin_topic_id', 1)
            fio = context.user_data.get('admin_fio', '')

            if fio and reset_attempts(fio, topic_id):
                await update.message.reply_text(
                    f"✅ Попытки для {fio} сброшены! Теперь снова 2 попытки.",
                    reply_markup=get_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "✅ Попытки сброшены!",
                    reply_markup=get_main_keyboard()
                )

            # Очищаем данные
            context.user_data['waiting_for_admin_password'] = False
            context.user_data.pop('admin_topic_id', None)
            context.user_data.pop('admin_fio', None)
        else:
            await update.message.reply_text(
                "❌ Неверный пароль администратора.",
                reply_markup=get_main_keyboard()
            )
            context.user_data['waiting_for_admin_password'] = False
        return

    # Проверка на ожидание пароля для админ-панели
    elif context.user_data.get('waiting_for_admin_panel_password'):
        if check_admin_password(text):
            await update.message.reply_text(
                "✅ Доступ разрешен! Вы вошли в админ-панель.",
                reply_markup=get_admin_keyboard()
            )
            context.user_data['waiting_for_admin_panel_password'] = False
            context.user_data['is_admin'] = True
        else:
            await update.message.reply_text(
                "❌ Неверный пароль администратора.",
                reply_markup=get_main_keyboard()
            )
            context.user_data['waiting_for_admin_panel_password'] = False
        return

    elif context.user_data.get('waiting_for_final_test_password'):
        if check_final_test_password(text):
            await update.message.reply_text(
                "✅ Пароль принят! Теперь введите ваше ФИО для начала итогового теста:"
            )
            context.user_data['waiting_for_final_test_password'] = False
            context.user_data['waiting_for_final_test_fio'] = True
        else:
            await update.message.reply_text(
                "❌ Неверный пароль для итогового теста.",
                reply_markup=get_menu_keyboard()
            )
            context.user_data['waiting_for_final_test_password'] = False
        return

    elif context.user_data.get('waiting_for_final_test_fio'):
        if text.strip():
            fio = text.strip()
            context.user_data['current_fio'] = fio
            context.user_data['waiting_for_final_test_fio'] = False

            # Начинаем финальный тест
            await start_final_test(update, context, user_id, fio)
        else:
            await update.message.reply_text("❌ Пожалуйста, введите корректные ФИО.")
        return

    # Основное меню
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
            "3. 'Инструкция' - это руководство\n"
            "4. 'Админ-панель' - доступ к отчетам\n\n"
            "5. '🎯 Итоговый тест' - финальный тест на 60 минут (60 вопросов)\n\n"
            "Перед началом тестирования необходимо ввести свои ФИО."
        )
        await update.message.reply_text(
            instruction_text,
            reply_markup=get_main_keyboard()
        )

    elif text == "Админ-панель":
        await update.message.reply_text(
            "🔐 Введите пароль администратора:"
        )
        context.user_data['waiting_for_admin_panel_password'] = True

    elif text == "📊 Получить отчет":
        if context.user_data.get('is_admin'):
            from data_storage import get_all_results

            results = get_all_results()
            if not results:
                await update.message.reply_text(
                    "📊 Отчет по тестированию\n\nНет данных о пройденных тестах.",
                    reply_markup=get_admin_keyboard()
                )
                return

            # Создаем отчет
            report = "📊 ОТЧЕТ ПО ТЕСТИРОВАНИЮ\n\n"
            report += "=" * 100 + "\n"
            report += "| №  | ФИО                          | Модуль | Название теста" + " " * 20 + "| Попытка | Результат | Дата и время           |\n"
            report += "=" * 100 + "\n"

            for i, record in enumerate(results, 1):
                topic_id = record.get('topic_id', 1)
                topic_name = TESTS.get(topic_id, {}).get('name', 'Неизвестный тест')

                if len(topic_name) > 30:
                    topic_name = topic_name[:27] + "..."

                fio = record.get('fio', 'Неизвестно')
                if len(fio) > 25:
                    fio = fio[:22] + "..."

                timestamp = record.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%d.%m.%Y %H:%M")
                    except:
                        time_str = timestamp[:16]
                else:
                    time_str = "Неизвестно"

                report += f"| {i:<3} | {fio:<25} | {topic_id:<6} | {topic_name:<30} | {record.get('attempt', 1):<8} | {record.get('percentage', 0):<6.1f}%  | {time_str:<20} |\n"

            report += "=" * 100 + "\n"
            report += f"\nВсего записей: {len(results)}"

            # Сохраняем в файл
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)

            # Отправляем файл
            await update.message.reply_document(
                document=open(filename, 'rb'),
                caption="📊 Отчет по тестированию",
                reply_markup=get_admin_keyboard()
            )

            # Удаляем временный файл
            os.remove(filename)
        else:
            await update.message.reply_text(
                "❌ У вас нет доступа к этой функции.",
                reply_markup=get_main_keyboard()
            )

    elif text == "📋 Отчет по итоговому тесту":
        if context.user_data.get('is_admin'):
            results = get_all_final_results()
            if not results:
                await update.message.reply_text(
                    "📊 Отчет по итоговому тесту\n\nНет данных о пройденных тестах.",
                    reply_markup=get_admin_keyboard()
                )
                return

            # Создаем отчет
            report = "📊 ОТЧЕТ ПО ИТОГОВОМУ ТЕСТУ\n\n"
            report += "=" * 90 + "\n"
            report += "| №  | ФИО                          | Результат | Время (мин) | Статус     | Дата и время           |\n"
            report += "=" * 90 + "\n"

            for i, record in enumerate(results, 1):
                fio = record.get('fio', 'Неизвестно')
                if len(fio) > 25:
                    fio = fio[:22] + "..."

                percentage = record.get('percentage', 0)
                time_spent = record.get('time_spent_minutes', 0)
                status = record.get('status', 'unknown')
                status_rus = "Завершен" if status == 'completed' else "Время вышло"

                timestamp = record.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%d.%m.%Y %H:%M")
                    except:
                        time_str = timestamp[:16]
                else:
                    time_str = "Неизвестно"

                report += f"| {i:<3} | {fio:<25} | {percentage:<6.1f}%   | {time_spent:<11.1f} | {status_rus:<10} | {time_str:<20} |\n"

            report += "=" * 90 + "\n"
            report += f"\nВсего записей: {len(results)}"

            # Сохраняем в файл
            filename = f"final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)

            # Отправляем файл
            await update.message.reply_document(
                document=open(filename, 'rb'),
                caption="📊 Отчет по итоговому тесту",
                reply_markup=get_admin_keyboard()
            )

            # Удаляем временный файл
            os.remove(filename)
        else:
            await update.message.reply_text(
                "❌ У вас нет доступа к этой функции.",
                reply_markup=get_main_keyboard()
            )

    elif text == "🎯 Итоговый тест":
        test_info = (
            "🎯 ИТОГОВЫЙ ТЕСТ\n\n"
            "• 60 вопросов\n"
            "• Ограничение по времени: 60 минут\n"
            "• Для доступа требуется пароль\n\n"
            "Уведомления о времени:\n"
            "• Через 30 минут\n"
            "• Через 50 минут\n"
            "• Через 55 минут\n\n"
            "По истечении 60 минут тест автоматически завершается.\n\n"
            "Введите пароль для доступа к итоговому тесту:"
        )
        await update.message.reply_text(
            test_info,
            reply_markup=get_menu_keyboard()
        )
        context.user_data['waiting_for_final_test_password'] = True

    elif text == "🔙 Назад":
        if context.user_data.get('is_admin'):
            await update.message.reply_text(
                "Возврат в главное меню",
                reply_markup=get_main_keyboard()
            )
            context.user_data['is_admin'] = False
        else:
            await update.message.reply_text(
                "Возврат в главное меню",
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

    else:
        await update.message.reply_text(
            "Я не понимаю эту команду. Пожалуйста, используйте кнопки ниже:",
            reply_markup=get_main_keyboard()
        )


async def start_final_test(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, fio: str):
    """Начать финальный тест"""
    from final_test_data import FINAL_TEST, start_final_test_session

    # Начинаем сессию
    session = start_final_test_session(user_id, fio)
    session['start_time'] = datetime.now()
    session['timer_started'] = True

    # Запускаем таймер
    await start_final_test_timer(update, context, user_id)

    # Отправляем первый вопрос
    question = FINAL_TEST['questions'][0]
    question_text = f"🎯 Итоговый тест\n\n⏱ Время: 60 минут\n❓ Вопрос 1/60\n\n{question['question']}"

    keyboard = get_final_test_keyboard(0)

    await update.message.reply_text(
        question_text,
        reply_markup=keyboard
    )


async def start_final_test_timer(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Запустить таймер для финального теста"""
    from final_test_data import get_final_test_session, FINAL_TEST

    # Отменяем предыдущий таймер, если есть
    if user_id in timer_tasks:
        timer_tasks[user_id].cancel()

    # Создаем задачу таймера
    timer_tasks[user_id] = asyncio.create_task(
        final_test_timer(update, context, user_id)
    )


async def final_test_timer(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Таймер для финального теста"""
    from final_test_data import get_final_test_session, FINAL_TEST

    try:
        session = get_final_test_session(user_id)
        if not session:
            return

        start_time = session['start_time']
        if not start_time:
            return

        # Уведомление через 30 минут
        await asyncio.sleep(30 * 60)  # 30 минут
        session = get_final_test_session(user_id)
        if session and not session['notifications_sent'][30]:
            await update.message.reply_text(
                "⏰ Прошло 30 минут из 60.\n"
                "У вас осталось 30 минут для завершения теста."
            )
            session['notifications_sent'][30] = True

        # Уведомление через 50 минут
        await asyncio.sleep(20 * 60)  # Еще 20 минут
        session = get_final_test_session(user_id)
        if session and not session['notifications_sent'][50]:
            await update.message.reply_text(
                "⏰ Прошло 50 минут из 60.\n"
                "Осталось 10 минут! Поторопитесь с завершением."
            )
            session['notifications_sent'][50] = True

        # Уведомление через 55 минут
        await asyncio.sleep(5 * 60)  # Еще 5 минут
        session = get_final_test_session(user_id)
        if session and not session['notifications_sent'][55]:
            await update.message.reply_text(
                "⏰ Прошло 55 минут из 60.\n"
                "Осталось 5 минут! Завершите тест как можно скорее."
            )
            session['notifications_sent'][55] = True

        # Завершение через 60 минут
        await asyncio.sleep(5 * 60)  # Еще 5 минут
        session = get_final_test_session(user_id)
        if session:
            await finish_final_test_by_timeout(update, context, user_id)

    except asyncio.CancelledError:
        # Таймер был отменен (тест завершен досрочно)
        pass
    except Exception as e:
        logging.error(f"Ошибка в таймере финального теста: {e}")


async def finish_final_test_by_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Завершить финальный тест по истечении времени"""
    from final_test_data import get_final_test_session, finish_final_test_session, calculate_final_test_score

    session = get_final_test_session(user_id)
    if not session:
        return

    # Рассчитываем время
    start_time = session['start_time']
    end_time = datetime.now()
    time_spent = (end_time - start_time).total_seconds() / 60  # в минутах

    # Рассчитываем результат
    percentage, score, total = calculate_final_test_score(session['answers'])

    # Сохраняем результат
    add_final_test_result(session['fio'], percentage, time_spent)

    # Завершаем сессию
    finish_final_test_session(user_id)

    # Отправляем результат
    result_text = (
        f"⏰ ВРЕМЯ ВЫШЛО!\n\n"
        f"🎯 Итоговый тест завершен\n"
        f"👤 ФИО: {session['fio']}\n"
        f"⏱ Затраченное время: {time_spent:.1f} минут\n"
        f"✅ Правильных ответов: {score}/{total}\n"
        f"📊 Результат: {percentage:.1f}%\n\n"
    )

    if percentage >= 80:
        result_text += "🎉 Отличный результат!"
    elif percentage >= 60:
        result_text += "👍 Хороший результат!"
    else:
        result_text += "📚 Необходимо повторить материал."

    await update.message.reply_text(
        result_text,
        reply_markup=get_menu_keyboard()
    )

    # Отменяем таймер
    if user_id in timer_tasks:
        timer_tasks.pop(user_id, None)


async def show_test_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать результаты тестирования"""
    user_id = update.message.from_user.id

    # Проверяем, есть ли сохраненное ФИО
    fio = context.user_data.get('current_fio', '')

    if not fio:
        await update.message.reply_text(
            "📊 Для просмотра результатов тестирования сначала необходимо ввести ФИО.\n\n"
            "Нажмите на кнопку тестирования и введите свои ФИО.",
            reply_markup=get_menu_keyboard()
        )
        return

    from data_storage import get_user_by_fio
    user_id_in_db, user_data = get_user_by_fio(fio)

    if not user_data:
        await update.message.reply_text(
            f"❌ Не удалось найти результаты для {fio}.",
            reply_markup=get_menu_keyboard()
        )
        return

    results_text = f"📊 Итоги тестирования\n\n👤 ФИО: {fio}\n\n"

    has_results = False
    for topic_id_str, percentage in user_data.get('test_results', {}).items():
        topic_id = int(topic_id_str)
        if topic_id in TOPIC_NAMES and percentage > 0:
            has_results = True
            topic_name = TOPIC_NAMES[topic_id]
            color = get_color_for_percentage(percentage)
            attempts = user_data.get('test_attempts', {}).get(topic_id_str, 0)
            attempts_left = 2 - attempts

            results_text += f"{color} {topic_name}\n"
            results_text += f"   Результат: {percentage:.1f}%\n"
            results_text += f"   Попыток использовано: {attempts}/2\n"
            results_text += f"   Осталось попыток: {attempts_left}\n\n"

    if not has_results:
        results_text += "📝 Вы еще не проходили тестирование."

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
        try:
            parts = query.data.split("_")
            topic_id = int(parts[2])

            # Сохраняем topic_id в контексте
            context.user_data['pending_test_id'] = topic_id

            # Проверяем, есть ли уже сохраненное ФИО
            fio = context.user_data.get('current_fio', '')

            if fio:
                # ФИО уже есть, проверяем историю
                history = get_user_test_history(fio, topic_id)

                if history['attempts'] < 2:
                    # Можно начать тест
                    start_test_session(user_id, fio, topic_id)
                    await send_question(update, context, user_id, topic_id, 0)
                else:
                    # Все попытки использованы
                    await query.edit_message_text(
                        f"❌ {fio}, вы использовали все 2 попытки для этого теста.\n\n"
                        f"📊 Ваш лучший результат: {history['percentage']:.1f}%\n\n"
                        "Для сброса попыток введите пароль администратора:"
                    )
                    context.user_data['waiting_for_admin_password'] = True
                    context.user_data['admin_topic_id'] = topic_id
                    context.user_data['admin_fio'] = fio
            else:
                # Запрашиваем ФИО
                await query.edit_message_text(
                    "📝 Перед началом тестирования необходимо ввести свои ФИО.\n\n"
                    "Пожалуйста, введите ваше ФИО (например: Иванов Иван Иванович):"
                )
                context.user_data['waiting_for_fio'] = True

        except (IndexError, ValueError) as e:
            logging.error(f"Ошибка обработки start_test: {e}, data: {query.data}")
            await query.edit_message_text(
                "Ошибка начала теста. Попробуйте еще раз.",
                reply_markup=None
            )

    elif query.data.startswith("answer_"):
        try:
            parts = query.data.split("_")
            if len(parts) >= 5:
                topic_id = int(parts[1])
                question_num = int(parts[2])
                answer_index = int(parts[3])
                answer_letter = parts[4]

                add_user_answer(user_id, [answer_letter])
                next_question(user_id)

                test_data = TESTS.get(topic_id)
                if test_data and question_num + 1 < len(test_data['questions']):
                    await send_question(update, context, user_id, topic_id, question_num + 1)
                else:
                    # Завершение теста
                    percentage, score, total = calculate_score(user_id, topic_id, test_data)
                    color = get_color_for_percentage(percentage)

                    fio = context.user_data.get('current_fio', 'Не указано')

                    result_text = (
                        f"🎯 Тест завершен!\n\n"
                        f"👤 ФИО: {fio}\n"
                        f"📚 Тема: {test_data['name']}\n"
                        f"✅ Правильных ответов: {score}/{total}\n"
                        f"📊 Результат: {color} {percentage:.1f}%\n\n"
                    )

                    if percentage >= 85:
                        result_text += "🎉 Отлично! Вы успешно прошли тест!"
                    elif percentage >= 50:
                        result_text += "👍 Хорошо, но есть над чем поработать."
                    else:
                        result_text += "📚 Необходимо повторить материал."

                    await query.edit_message_text(
                        result_text,
                        reply_markup=None
                    )
            else:
                logging.error(f"Неверный формат callback_data: {query.data}")
                await query.edit_message_text(
                    "Ошибка обработки ответа. Попробуйте еще раз.",
                    reply_markup=None
                )

        except (IndexError, ValueError, KeyError) as e:
            logging.error(f"Ошибка обработки answer: {e}, data: {query.data}")
            await query.edit_message_text(
                "Произошла ошибка при обработке ответа. Пожалуйста, попробуйте еще раз.",
                reply_markup=None
            )

    elif query.data.startswith("final_answer_"):
        try:
            parts = query.data.split("_")
            question_num = int(parts[2])
            answer_index = int(parts[3])
            answer_letter = parts[4]

            from final_test_data import get_final_test_session, update_final_test_answer, next_final_question, \
                FINAL_TEST

            session = get_final_test_session(user_id)
            if not session:
                await query.edit_message_text(
                    "Сессия теста не найдена. Пожалуйста, начните тест заново.",
                    reply_markup=None
                )
                return

            # Сохраняем ответ
            update_final_test_answer(user_id, [answer_letter])

            # Переходим к следующему вопросу
            next_final_question(user_id)

            # Проверяем, есть ли еще вопросы
            if session['current_question'] < len(FINAL_TEST['questions']):
                # Отправляем следующий вопрос
                question = FINAL_TEST['questions'][session['current_question']]
                question_text = (
                    f"🎯 Итоговый тест\n\n"
                    f"⏱ Время: 60 минут\n"
                    f"❓ Вопрос {session['current_question'] + 1}/60\n\n"
                    f"{question['question']}"
                )

                keyboard = get_final_test_keyboard(session['current_question'])
                await query.edit_message_text(question_text, reply_markup=keyboard)
            else:
                # Все вопросы пройдены, завершаем тест досрочно
                await finish_final_test_early(update, context, user_id)

        except Exception as e:
            logging.error(f"Ошибка обработки ответа в финальном тесте: {e}")
            await query.edit_message_text(
                "Ошибка обработки ответа. Пожалуйста, попробуйте еще раз.",
                reply_markup=None
            )

        # Обработка досрочного завершения финального теста

    elif query.data == "final_finish":
        await finish_final_test_early(update, context, user_id)


async def finish_final_test_early(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Завершить финальный тест досрочно"""
    from final_test_data import get_final_test_session, finish_final_test_session, calculate_final_test_score

    session = get_final_test_session(user_id)
    if not session:
        await update.callback_query.edit_message_text(
            "Сессия теста не найдена.",
            reply_markup=None
        )
        return

    # Рассчитываем время
    start_time = session['start_time']
    end_time = datetime.now()
    time_spent = (end_time - start_time).total_seconds() / 60  # в минутах

    # Рассчитываем результат
    percentage, score, total = calculate_final_test_score(session['answers'])

    # Сохраняем результат
    add_final_test_result(session['fio'], percentage, time_spent)

    # Завершаем сессию
    finish_final_test_session(user_id)

    # Отправляем результат
    result_text = (
        f"🏁 ТЕСТ ЗАВЕРШЕН ДОСРОЧНО\n\n"
        f"🎯 Итоговый тест завершен\n"
        f"👤 ФИО: {session['fio']}\n"
        f"⏱ Затраченное время: {time_spent:.1f} минут\n"
        f"✅ Правильных ответов: {score}/{total}\n"
        f"📊 Результат: {percentage:.1f}%\n\n"
    )

    if percentage >= 80:
        result_text += "🎉 Отличный результат!"
    elif percentage >= 60:
        result_text += "👍 Хороший результат!"
    else:
        result_text += "📚 Необходимо повторить материал."

    if hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(
            result_text,
            reply_markup=None
        )
    else:
        await update.message.reply_text(
            result_text,
            reply_markup=get_menu_keyboard()
        )

    # Отменяем таймер
    if user_id in timer_tasks:
        timer_tasks[user_id].cancel()
        timer_tasks.pop(user_id, None)



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


# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    error = context.error
    logging.error(f"Произошла ошибка: {error}", exc_info=True)


# Основная функция
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
    application.add_error_handler(error_handler)

    print("Бот запущен...")
    application.run_polling(
        poll_interval=1.0,
        timeout=30,
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()