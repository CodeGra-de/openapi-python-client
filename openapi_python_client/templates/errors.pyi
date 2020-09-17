from httpx import Response


class ApiResponseError(Exception):
    """ An exception raised when an unknown response occurs """

    def __init__(self, *, response: Response):
        super().__init__()
        self.response: Response = response
        try:
            self.json_data = response.json()
        except:
            self.json_data = None

    def __str__(self) -> str:
        return f'{super().__str__()}: {self.response!r} ({self.json_data})'
