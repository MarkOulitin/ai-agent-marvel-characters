FROM python:3.12-alpine

WORKDIR /home
COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY ./server ./

CMD ["python3", "server.py"]