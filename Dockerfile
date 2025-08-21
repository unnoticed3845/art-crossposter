FROM python:3.11-alpine
LABEL org.opencontainers.image.source=https://github.com/unnoticed3845/art-crossposter

WORKDIR /opt/artcrossposter

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./src ./src
COPY ./main.py .

CMD ["python3", "main.py"]
