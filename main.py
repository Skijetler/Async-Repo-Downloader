import platform
import random
import re
import string
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from asyncio import Semaphore, gather, run
from hashlib import sha256
from http import HTTPStatus
from os import getenv
from os import name as os_name
from pathlib import Path
from typing import Any, Coroutine

from aiofiles import open as aio_open
from aiofiles import os as aio_os
from aiohttp import ClientResponse, ClientSession

UrlRegex: re.Pattern[str] = re.compile(
    r'(?P<protocol>(\w+))://' +
    r'(?P<hostname>([\w\-\.]+))/' +
    r'(?P<path>([-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*))',
)
RandStrLen: int = 15
RandStrCmd: str = (
    "head /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c " +
    str(RandStrLen)
)


async def get_request(session: ClientSession, url: str) -> ClientResponse:
    """Request data from the specified address using the GET method."""
    resp: ClientResponse = await session.get(url=url)
    if resp.status != HTTPStatus.OK:
        raise ConnectionError(
            'Error on trying to get {url}: {status}'.format(
                url=url,
                status=resp.status,
            ),
        )
    return resp


async def download_file(
    session: ClientSession, url: str, path: Path, cor: int,
) -> None:
    """Download file for by the specified path."""
    async with Semaphore(cor):
        r_file: ClientResponse = await get_request(session, url)
        async with aio_open(path, 'wb') as b_file:
            await b_file.write(await r_file.content.read())


async def calc_hash(file_path: Path):
    """Calculate hash of file by given path."""
    if not file_path.exists():
        raise FileNotFoundError('File not Found')

    file_hash = sha256()
    chunk_size: int = 4096
    async with aio_open(file_path, 'rb') as b_file:
        while True:
            chunk: bytes = await b_file.read(chunk_size)
            if not chunk:
                break
            file_hash.update(chunk)
        return file_hash


async def print_hash(
    download_file_future: Coroutine[Any, Any, None],
    calc_hash_future: Coroutine[Any, Any, Any],
    file_name: str,
) -> None:
    """Print hash of downloaded file."""
    await download_file_future
    file_hash = await calc_hash_future
    sys.stdout.write(
        '{file_name} hash: {file_hash_hex}\n'.format(
            file_name=file_name,
            file_hash_hex=file_hash.hexdigest(),
        ),
    )


async def parse_repo(
    session_info: tuple[ClientSession, int],
    base_url: str,
    repo_entities: list,
    tasks: list,
    path: Path,
) -> None:
    """Parse directories for files, transfers files for download."""
    for entity in repo_entities:
        if not entity.get('type'):
            raise KeyError("Not valid response, key 'type' not found")

        if entity.get('type') == 'file':
            tasks.append(
                print_hash(
                    download_file_future=download_file(
                        session=session_info[0],
                        url=entity.get('download_url'),
                        path=(path / entity.get('name')),
                        cor=session_info[1],
                    ),
                    calc_hash_future=calc_hash(path / entity.get('name')),
                    file_name=str(path / entity.get('name')),
                ),
            )

        elif entity.get('type') == 'dir':
            path: Path = path / entity.get('path')
            await aio_os.makedirs(path, exist_ok=True)
            new_resp: ClientResponse = await get_request(
                session=session_info[0],
                url='{base_url}/{path}'.format(
                    base_url=base_url,
                    path=path.name,
                ),
            )
            await parse_repo(
                session_info=(session_info[0], session_info[1]),
                base_url='{base_url}/{path}'.format(
                    base_url=base_url,
                    path=path.name,
                ),
                repo_entities=await new_resp.json(),
                tasks=tasks,
                path=path,
            )


async def create_temp_dir(args: Namespace, repo_name: str) -> None:
    """Create temp dir for downloading repo."""
    sys.stdout.write(
        'Downloading {repo_name} repo to {dir} folder\n'.format(
            repo_name=repo_name,
            dir=args.dir,
        ),
    )
    await aio_os.makedirs(args.dir, exist_ok=True)


async def get_repo_info(
    session: ClientSession, protocol: str, hostname: str, path: str,
) -> tuple[str, str]:
    """Return repo name and api url for downloadnig repo files."""
    repo_name: str
    api_files_url: str
    if 'gitea' in hostname:
        api_info_url = '{0}://{1}/api/v1/repos/{2}'.format(
            protocol,
            hostname,
            path,
        )
        api_files_url = '{0}://{1}/api/v1/repos/{2}/contents'.format(
            protocol,
            hostname,
            path,
        )
        repo_info: ClientResponse = await get_request(
            session=session,
            url=api_info_url,
        )
        repo_name = (await repo_info.json()).get('name')
    elif 'github' in hostname:
        api_info_url = '{0}://api.github.com/search/repositories?q={1}'.format(
            protocol,
            path,
        )
        api_files_url = '{0}://api.github.com/repos/{1}/contents'.format(
            protocol,
            path,
        )
        repo_info: ClientResponse = await get_request(
            session=session,
            url=api_info_url,
        )
        repo_name = (await repo_info.json()).get('items')[0].get('name')

    return repo_name, api_files_url


async def main(args: Namespace) -> None:
    """Parse url, get session and call parsing function."""
    url_dict = (re.match(UrlRegex, args.url)).groupdict()

    async with ClientSession() as session:
        repo_name, api_files_url = await get_repo_info(
            session=session,
            protocol=url_dict['protocol'],
            hostname=url_dict['hostname'],
            path=url_dict['path'],
        )
        await create_temp_dir(args=args, repo_name=repo_name)
        tasks = []
        repo_contents: ClientResponse = await get_request(
            session=session,
            url=api_files_url,
        )
        await parse_repo(
            session_info=(session, args.streams),
            base_url=api_files_url,
            repo_entities=(await repo_contents.json()),
            tasks=tasks,
            path=Path(args.dir),
        )
        await gather(*tasks)


if __name__ == '__main__':  # pragma: no cover
    parser = ArgumentParser(
        prog='Repo Downloader',
        description='async donwload git repo from given url',
    )

    rand_str: str
    tmp_dir: str

    if platform.system() == 'Darwin':
        tmp_dir = getenv('TMPDIR')
        rand_str = ''
    elif os_name == 'posix':
        tmp_dir = '/tmp/'
        rand_str = subprocess.check_output(RandStrCmd, shell=True, text=True)
    else:
        tmp_dir = '{0}\\'.format(getenv('TEMP'))
        rand_str = ''.join(
            random.choices(
                string.ascii_letters + string.digits,
                k=RandStrLen,
            ),
        )

    parser.add_argument(
        '--url',
        default='https://gitea.radium.group/radium/project-configuration',
        help='Git Repo URL',
    )
    parser.add_argument(
        '-s',
        '--streams',
        default=3,
        help='set amount of streams for downloading',
    )
    parser.add_argument(
        '-d',
        '--dir',
        default=(tmp_dir + rand_str),
        help='set the folder where you want the repo to be downloaded',
    )

    args = parser.parse_args()

    try:
        run(main(args))
    except KeyboardInterrupt:
        sys.exit(0)
