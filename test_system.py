from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from data_storage import *

# Пароль администратора
ADMIN_PASSWORD = "admin123"

# Временное хранение сессий (только во время работы бота)
user_sessions = {}


def get_user_session(user_id):
    """Получить сессию пользователя"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'current_test': None,
            'current_question': 0,
            'user_answers': [],
            'temp_fio': None,
            'pending_test_id': None
        }
    return user_sessions[user_id]


def get_test_keyboard(topic_id):
    """Клавиатура для начала тестирования"""
    keyboard = [[InlineKeyboardButton("Начать тестирование", callback_data=f"start_test_{topic_id}")]]
    return InlineKeyboardMarkup(keyboard)


def get_answer_keyboard(question_num, options, topic_id):
    """Клавиатура с вариантами ответов"""
    keyboard = []
    for i, option in enumerate(options):
        letter = chr(97 + i)  # a, b, c, d
        keyboard.append([InlineKeyboardButton(
            option,
            callback_data=f"answer_{topic_id}_{question_num}_{i}_{letter}"
        )])
    return InlineKeyboardMarkup(keyboard)


def can_take_test(fio, topic_id):
    """Проверка возможности прохождения теста"""
    user_id, user_data = get_user_by_fio(fio)
    if user_data:
        attempts = user_data['test_attempts'].get(str(topic_id), 0)
        return attempts < 2
    return True  # Новый пользователь может пройти тест


def get_attempts_left(fio, topic_id):
    """Получить количество оставшихся попыток"""
    user_id, user_data = get_user_by_fio(fio)
    if user_data:
        attempts = user_data['test_attempts'].get(str(topic_id), 0)
        return 2 - attempts
    return 2  # Новый пользователь имеет 2 попытки


def start_test_session(user_id, fio, topic_id):
    """Начать сессию тестирования"""
    session = get_user_session(user_id)
    session['current_test'] = topic_id
    session['current_question'] = 0
    session['user_answers'] = []
    session['temp_fio'] = fio


def add_user_answer(user_id, answer):
    """Добавить ответ пользователя"""
    session = get_user_session(user_id)
    session['user_answers'].append(answer)


def next_question(user_id):
    """Перейти к следующему вопросу"""
    session = get_user_session(user_id)
    session['current_question'] += 1


def calculate_score(user_id, topic_id, test_data):
    """Рассчитать результат теста"""
    session = get_user_session(user_id)
    user_answers = session['user_answers']
    correct_answers = [q['correct_answers'] for q in test_data['questions']]

    score = 0
    for i, (user_answer, correct_answer) in enumerate(zip(user_answers, correct_answers)):
        if set(user_answer) == set(correct_answer):
            score += 1

    percentage = (score / len(test_data['questions'])) * 100

    # Сохраняем результат
    if session['temp_fio']:
        user_id_in_db, user_data = get_user_by_fio(session['temp_fio'])
        if not user_id_in_db:
            # Создаем нового пользователя
            user_id_in_db, user_data = create_user(session['temp_fio'])

        # Получаем текущее количество попыток
        current_attempts = user_data['test_attempts'].get(str(topic_id), 0)
        new_attempt = current_attempts + 1

        # Обновляем результат
        update_user_test_result(user_id_in_db, topic_id, percentage, new_attempt)

    return percentage, score, len(test_data['questions'])


def get_color_for_percentage(percentage):
    """Получить цвет для процентов"""
    if percentage >= 85:
        return "🟢"  # зеленый
    elif percentage >= 50:
        return "🟡"  # желтый
    else:
        return "🔴"  # красный


def reset_attempts(fio, topic_id):
    """Сбросить попытки пользователя"""
    user_id, user_data = get_user_by_fio(fio)
    if user_data:
        user_data['test_attempts'][str(topic_id)] = 0
        user_data['test_results'][str(topic_id)] = 0
        data = load_data()
        data['users'][user_id] = user_data
        save_data(data)
        return True
    return False


def check_admin_password(password):
    """Проверить пароль администратора"""
    return password == ADMIN_PASSWORD


def get_user_test_history(fio, topic_id):
    """Получить историю тестирования пользователя"""
    user_id, user_data = get_user_by_fio(fio)
    if user_data:
        attempts = user_data['test_attempts'].get(str(topic_id), 0)
        percentage = user_data['test_results'].get(str(topic_id), 0)

        return {
            'exists': True,
            'attempts': attempts,
            'percentage': percentage,
            'can_take_test': attempts < 2
        }

    return {'exists': False, 'attempts': 0, 'percentage': 0, 'can_take_test': True}