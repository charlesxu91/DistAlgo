FROM python:3.11-slim

WORKDIR /app
COPY setup.cfg setup.py README.md /app/
COPY src /app/src
COPY examples /app/examples
COPY scripts /app/scripts

RUN python -m pip install --no-cache-dir -e .

CMD ["python", "-m", "distalgo.cli", "list-algorithms"]
