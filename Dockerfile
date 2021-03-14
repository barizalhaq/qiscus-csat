FROM python:3-alpine

WORKDIR /usr/src/app

COPY requirements.txt .

RUN apk update
RUN apk add --no-cache postgresql-libs
RUN apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev
RUN python3 -m pip install -r requirements.txt --no-cache-dir
RUN apk --purge del .build-deps

COPY . .

CMD ["python3", "run.py"]