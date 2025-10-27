init:
	uv venv --python 3.10
	uv init && rm hello.py
	uv tool install black

install:
	. .venv/bin/activate
	# uv pip install --all-extras --requirement pyproject.toml
	uv add -r requirements.txt

delete:
	rm uv.lock pyproject.toml .python-version && rm -rf .venv

env:
	cp .env.example .env

jupyter:
	uv run jupyter lab & 