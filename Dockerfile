FROM python:3.8
COPY ./requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
ADD ./src /src
ENTRYPOINT ["python", "/src/fastnetmon_notify.py"] 