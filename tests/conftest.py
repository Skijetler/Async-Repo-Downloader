from pathlib import Path

import pytest_asyncio
from aiohttp import ClientSession
from argparse import Namespace

from tests.mocks import FakeSession


@pytest_asyncio.fixture()
async def temp_file(tmp_path: callable) -> Path:
    test_file: Path = tmp_path / 'test_file.txt'
    test_file.write_text(
        'Lorem ipsum dolor sit amet, consectetuer adipiscing elit. ' +
        'Aenean commodo ligula eget dolor. Aenean massa. ' +
        'Cum sociis natoque penatibus et magnis dis parturient montes, ' +
        'nascetur ridiculus mus.',
    )
    return test_file


@pytest_asyncio.fixture()
async def real_session() -> ClientSession:
    """Creating a real session."""
    async with ClientSession() as session:
        yield session


@pytest_asyncio.fixture()
async def fake_session() -> FakeSession:
    """Creating a fake session."""
    return FakeSession()


@pytest_asyncio.fixture()
async def main_args(tmp_path: callable) -> Namespace:
    test_dir = tmp_path / 'test_repo_dir'
    test_dir.mkdir()
    return Namespace(
        url='https://gitea.radium.group/radium/project-configuration',
        streams=3,
        dir=str(test_dir),
    )
