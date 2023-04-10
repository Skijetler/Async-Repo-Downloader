import json
from http import HTTPStatus


class MockClientResponse:
    def __init__(self, text: str, status: int) -> None:
        self._text = text
        self.status = status

    async def json(self):
        return json.loads(self._text)


class FakeSession:
    async def get(self, url: str) -> MockClientResponse:
        if url == 'fake_dir_url/nitpick':
            return MockClientResponse(json.dumps([]), HTTPStatus.OK)
