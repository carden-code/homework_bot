import json
import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from exeptions import (EndpointUnavailableError, ResponseEmptyError,
                       UndocumentedStatusError)

# Подгружаем переменные окружения.
load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

# Подключаем логирование.
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logging.StreamHandler(sys.stdout)


def send_message(bot, message) -> None:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.info('Сообщение удачно отправлено')
    except Exception as error:
        logging.error(f'Сбой при отправке сообщения в Telegram - {error}')


def get_api_answer(current_timestamp) -> json:
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise EndpointUnavailableError()
    return response.json()


def check_response(response) -> list:
    """Проверяет ответ API на корректность."""
    keys_to_check = ['homeworks', 'current_date']
    if not response:
        raise ResponseEmptyError()

    if not isinstance(response, dict):
        raise TypeError()

    for key in keys_to_check:
        if key not in response:
            mess = f'Ключ - {key} отсутствует в ответе API'
            raise KeyError(mess)

    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Домашки приходят не в виде списка в ответ от API')
    return homeworks


def parse_status(homework) -> str:
    """Извлекает из информации о конкретной
        домашней работе статус этой работы."""
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise KeyError('Отсутствует ключ - homework_name')

    homework_status = homework.get('status')
    if not homework_status:
        raise KeyError('Отсутствует ключ - homework_status')

    if homework_status not in HOMEWORK_STATUSES:
        raise UndocumentedStatusError

    verdict = HOMEWORK_STATUSES.get(homework_status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    return False


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Отсутствие обязательных переменных окружения'
            'во время запуска бота'
        )
        os._exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0

    current_status = 0
    error_dict_counter = {}

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                status = parse_status(homeworks[0])
                if current_status != status:
                    current_status = status
                    send_message(bot, status)
            else:
                logging.debug('Отсутствие в ответе новых статусов')

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(error)

            if not error_dict_counter.get(error.__class__):
                send_message(bot, message)
                error_dict_counter[error.__class__] = 1

            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
