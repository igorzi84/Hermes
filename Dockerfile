FROM python:3.13-slim

RUN apt-get update && apt-get install -y curl && apt-get clean

WORKDIR /app

RUN pip install go-task-bin

COPY hermes/ /app/
COPY taskfile.yaml pyproject.toml uv.lock /app/

RUN task install_devenv

ENV PATH="/root/.local/bin:$PATH"

ENTRYPOINT ["uv", "run", "main.py"]

CMD ["breaking", "depricated"]
