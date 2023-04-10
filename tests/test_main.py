from pathlib import Path

import pytest
from aiohttp import ClientResponse
from http import HTTPStatus

from main import get_request, download_file, calc_hash, print_hash, parse_repo, main
from tests.constants import FAKE_HASH, REAL_HASH, REAL_FILE, FAKE_FILE, FAKE_DIR


class TestsDownload:
    @pytest.mark.asyncio()
    async def test_get_request_pass(self, real_session: callable) -> None:
        response: ClientResponse = await get_request(real_session, 'https://ya.ru/')
        assert response.status == HTTPStatus.OK

    @pytest.mark.asyncio()
    async def test_get_request_fail(self, real_session: callable) -> None:
        with pytest.raises(ConnectionError):
            await get_request(real_session, 'https://yandex.com/void')

    @pytest.mark.asyncio()
    async def test_download_file_pass(self, real_session: callable, tmp_path: callable) -> None:
        await download_file(real_session, REAL_FILE['download_url'], tmp_path / REAL_FILE['path'], 3)
        assert (tmp_path / REAL_FILE['path']).exists()

    @pytest.mark.asyncio()
    async def test_gitea_parse_repo_key_error_pass(self, fake_session: callable, tmp_path: callable) -> None:
        with pytest.raises(KeyError):
            await parse_repo((fake_session, 3), FAKE_FILE['download_url'], [FAKE_FILE], [], tmp_path)

    @pytest.mark.asyncio()
    async def test_gitea_parse_repo_add_task(self, fake_session: callable, tmp_path: callable) -> None:
        tasks: list = []
        await parse_repo((fake_session, 3), REAL_FILE['download_url'], [REAL_FILE], tasks, tmp_path)
        assert len(tasks) == 1

    @pytest.mark.asyncio()
    async def test_parse_catalog_create_dir(self, fake_session: callable, tmp_path: callable) -> None:
        await parse_repo((fake_session, 3), FAKE_DIR['download_url'], [FAKE_DIR], [], tmp_path)
        assert len(list(tmp_path.rglob('*'))) == 1


class TestsHash:
    @pytest.mark.asyncio()
    async def test_hash_filepath_fail(self) -> None:
        with pytest.raises(FileNotFoundError):
            await calc_hash(Path('void://filepath/file_name'))

    @pytest.mark.asyncio()
    async def test_hash_calculation_fail(self, temp_file: callable) -> None:
        file_hash = await calc_hash(temp_file)
        assert FAKE_HASH != file_hash.hexdigest(), "Хэш не совпадает"

    @pytest.mark.asyncio()
    async def test_hash_calculation_pass(self, temp_file: callable) -> None:
        file_hash = await calc_hash(temp_file)
        assert REAL_HASH == file_hash.hexdigest(), "Хэши одинаковые"

    @pytest.mark.asyncio()
    async def test_hash_print_pass(self, real_session: callable, tmp_path: callable, capsys: callable):
        await print_hash(
            download_file(
                real_session, REAL_FILE['download_url'],
                tmp_path / REAL_FILE['path'],
                3
            ),
            calc_hash(
                tmp_path / REAL_FILE['path']
            ),
            str(tmp_path / REAL_FILE['path'])
        )
        assert 'hash' in capsys.readouterr().out


class TestsMain:
    @pytest.mark.asyncio()
    async def test_main_output_pass(self, main_args: callable, capsys: callable) -> None:
        await main(main_args)
        assert 'Downloading' in capsys.readouterr().out
