restore:
	poetry install
	pre-commit install

test:
	poetry run pytest tests --show-capture=stdout

format:
	poetry run black dexml tests
	poetry run isort dexml tests

type:
	poetry run mypy dexml

check:
	poetry run pylint -E dexml

style:
	poetry run pylint -E dexml
