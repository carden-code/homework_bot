import json
import logging
import os
import sys
import time
from http import HTTPStatus

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


HOMEWORK_VERDICTS = {
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
logger = logging.getLogger(__name__)


def send_message(bot, message) -> bool:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.info('Сообщение удачно отправлено')
        return True
    except Exception as error:
        logger.error(f'Сбой при отправке сообщения в Telegram - {error}')
        return False


def get_api_answer(current_timestamp) -> json:
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if response.status_code != HTTPStatus.OK:
            raise EndpointUnavailableError()
    except Exception as error:
        logger.error(error)
        raise Exception(error)

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
    """Извлекает статус о конкретной домашней работе."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Отсутствует ключ - homework_name')

    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError('Отсутствует ключ - homework_status')

    if homework_status not in HOMEWORK_VERDICTS:
        raise UndocumentedStatusError

    verdict = HOMEWORK_VERDICTS.get(homework_status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    environment_variables = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(environment_variables)


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
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
                logger.debug('Отсутствие в ответе новых статусов')

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(error)

            if not error_dict_counter.get(error.__class__):
                if send_message(bot, message):
                    error_dict_counter[error.__class__] = 1

            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
