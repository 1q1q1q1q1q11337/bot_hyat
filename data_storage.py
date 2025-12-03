import json
import os
from datetime import datetime

DATA_FILE = "user_data.json"
RESULTS_FILE = "test_results.json"
FINAL_RESULTS_FILE = "final_test_results.json"


def load_data():
    """Загрузить данные из файлов"""
    data = {'users': {}, 'results': [], 'final_results': []}

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data['users'] = json.load(f)
        except:
            data['users'] = {}

    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                data['results'] = json.load(f)
        except:
            data['results'] = []

    if os.path.exists(FINAL_RESULTS_FILE):
        try:
            with open(FINAL_RESULTS_FILE, 'r', encoding='utf-8') as f:
                data['final_results'] = json.load(f)
        except:
            data['final_results'] = []

    return data


def save_data(data):
    """Сохранить данные в файлы"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data['users'], f, ensure_ascii=False, indent=2)

    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data['results'], f, ensure_ascii=False, indent=2)

    with open(FINAL_RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data['final_results'], f, ensure_ascii=False, indent=2)


def get_user_by_fio(fio):
    """Найти пользователя по ФИО"""
    data = load_data()
    fio_lower = fio.lower().strip()

    for user_id, user_data in data['users'].items():
        if user_data.get('fio', '').lower() == fio_lower:
            return user_id, user_data

    return None, None


def create_user(fio):
    """Создать нового пользователя"""
    data = load_data()

    # Генерируем новый ID
    user_id = str(int(datetime.now().timestamp() * 1000))

    data['users'][user_id] = {
        'fio': fio,
        'test_attempts': {},
        'test_results': {},
        'created_at': datetime.now().isoformat()
    }

    save_data(data)
    return user_id, data['users'][user_id]


def update_user_test_result(user_id, topic_id, percentage, attempt):
    """Обновить результат теста пользователя"""
    data = load_data()

    if user_id in data['users']:
        data['users'][user_id]['test_attempts'][str(topic_id)] = attempt
        data['users'][user_id]['test_results'][str(topic_id)] = percentage

        # Добавляем запись в историю результатов
        result_record = {
            'user_id': user_id,
            'fio': data['users'][user_id]['fio'],
            'topic_id': topic_id,
            'percentage': percentage,
            'attempt': attempt,
            'timestamp': datetime.now().isoformat()
        }
        data['results'].append(result_record)

        save_data(data)
        return True

    return False


def get_user_test_info(user_id, topic_id):
    """Получить информацию о тестах пользователя"""
    data = load_data()

    if user_id in data['users']:
        attempts = data['users'][user_id]['test_attempts'].get(str(topic_id), 0)
        percentage = data['users'][user_id]['test_results'].get(str(topic_id), 0)
        fio = data['users'][user_id].get('fio', '')

        return {
            'fio': fio,
            'attempts': attempts,
            'percentage': percentage,
            'can_take_test': attempts < 2
        }

    return None


def get_all_results():
    """Алиас для get_all_test_results (для обратной совместимости)"""
    return get_all_test_results()


def get_all_test_results():
    """Получить все результаты обычных тестов"""
    data = load_data()
    return data['results']


def get_all_final_results():
    """Получить все результаты финального теста"""
    data = load_data()
    return data['final_results']


def add_final_test_result(fio, percentage, time_spent_minutes):
    """Добавить результат финального теста"""
    data = load_data()

    result_record = {
        'fio': fio,
        'percentage': percentage,
        'time_spent_minutes': time_spent_minutes,
        'timestamp': datetime.now().isoformat(),
        'status': 'completed' if percentage > 0 else 'timeout'
    }

    data['final_results'].append(result_record)
    save_data(data)
    return True