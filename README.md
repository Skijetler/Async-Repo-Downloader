# Async-Repo-Downloader

Asynchronous python script that downloads the HEAD contents of the repository
https://gitea.radium.group/radium/project-configuration in a temporary folder
of 3 streams. After performing all asynchronous tasks, the script counts sha256
hashes from each downloaded file.

Tests are written for the script on Pytest

### Clone the repository and enter:
```
git clone https://github.com/Skijetler/Async-Repo-Downloader.git && cd Async-Repo-Downloader
```
### Install poetry:
```
pip install poetry
```
##### Installing dependencies:
```
poetry install
```
##### Running the script:
```
poetry run python main.py
```
##### Checking by linter:
```
poetry run flake8 main.py
```
##### Running tests:
```
poetry run pytest -vv
```
##### Show test coverage:
```
poetry run pytest --cov-report term-missing --cov=. --cov-report xml
```