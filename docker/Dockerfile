FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["pytest"]
