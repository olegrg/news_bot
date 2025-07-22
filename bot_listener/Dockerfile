FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV API_ID=${API_ID}
ENV API_HASH=${API_HASH}
ENV PHONE_NUMBER=${PHONE_NUMBER}

CMD ["python", "main.py"]