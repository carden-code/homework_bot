class EndpointUnavailableError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return f'EndpointUnavailableError, {self.message}'
        return 'EndpointUnavailableError - Эндпоинт не доступен.'


class UndocumentedStatusError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return f'UndocumentedStatusError, {self.message}'
        return (
            'UndocumentedStatusError - '
            'недокументированный статус домашней работы в ответе от API.'
        )


class ResponseEmptyError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return f'ResponseEmptyError, {self.message}'
        return (
            'ResponseEmptyError - ответ от API содержит пустой словарь.'
        )
