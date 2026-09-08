FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py analytics.py prepare_data.py ./
COPY assets ./assets
COPY docs ./docs
COPY data/processed ./data/processed
EXPOSE 8050
CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:8050", "--workers", "1", "--threads", "4", "--timeout", "120"]
