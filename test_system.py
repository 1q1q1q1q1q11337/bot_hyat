from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# Хранение данных пользователей
user_data = {}

# Пароль администратора
ADMIN_PASSWORD = "admin123"


def initialize_user(user_id):
    """Инициализация данных пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {
            'test_attempts': {1: 0},  # попытки по темам
            'test_results': {1: 0},  # результаты по темам
            'current_test': None,  # текущий тест
            'current_question': 0,  # текущий вопрос
            'user_answers': []  # ответы пользователя
        }


def get_test_keyboard(topic_id):
    """Клавиатура для начала тестирования"""
    keyboard = [[InlineKeyboardButton("Начать тестирование", callback_data=f"start_test_{topic_id}")]]
    return InlineKeyboardMarkup(keyboard)


def get_answer_keyboard(question_num, options, topic_id):
    """Клавиатура с вариантами ответов"""
    keyboard = []
    for i, option in enumerate(options):
        letter = chr(97 + i)  # a, b, c, d
        keyboard.append([InlineKeyboardButton(option, callback_data=f"answer_{topic_id}_{question_num}_{letter}")])
    return InlineKeyboardMarkup(keyboard)


def can_take_test(user_id, topic_id):
    """Проверка возможности прохождения теста"""
    initialize_user(user_id)
    return user_data[user_id]['test_attempts'].get(topic_id, 0) < 2


def get_attempts_left(user_id, topic_id):
    """Получить количество оставшихся попыток"""
    initialize_user(user_id)
    return 2 - user_data[user_id]['test_attempts'].get(topic_id, 0)


def start_test_session(user_id, topic_id):
    """Начать сессию тестирования"""
    initialize_user(user_id)
    user_data[user_id]['current_test'] = topic_id
    user_data[user_id]['current_question'] = 0
    user_data[user_id]['user_answers'] = []
    user_data[user_id]['test_attempts'][topic_id] = user_data[user_id]['test_attempts'].get(topic_id, 0) + 1


def add_user_answer(user_id, answer):
    """Добавить ответ пользователя"""
    initialize_user(user_id)
    user_data[user_id]['user_answers'].append(answer)


def next_question(user_id):
    """Перейти к следующему вопросу"""
    initialize_user(user_id)
    user_data[user_id]['current_question'] += 1


def calculate_score(user_id, topic_id, test_data):
    """Рассчитать результат теста"""
    initialize_user(user_id)
    user_answers = user_data[user_id]['user_answers']
    correct_answers = [q['correct_answers'] for q in test_data['questions']]

    score = 0
    for i, (user_answer, correct_answer) in enumerate(zip(user_answers, correct_answers)):
        if set(user_answer) == set(correct_answer):
            score += 1

    percentage = (score / len(test_data['questions'])) * 100
    user_data[user_id]['test_results'][topic_id] = percentage
    return percentage, score, len(test_data['questions'])


def get_color_for_percentage(percentage):
    """Получить цвет для процентов"""
    if percentage >= 85:
        return "🟢"  # зеленый
    elif percentage >= 50:
        return "🟡"  # желтый
    else:
        return "🔴"  # красный


def reset_attempts(user_id, topic_id):
    """Сбросить попытки пользователя"""
    initialize_user(user_id)
    user_data[user_id]['test_attempts'][topic_id] = 0
    user_data[user_id]['test_results'][topic_id] = 0


def check_admin_password(password):
    """Проверить пароль администратора"""
    return password == ADMIN_PASSWORD