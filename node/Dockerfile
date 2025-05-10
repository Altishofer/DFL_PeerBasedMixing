FROM python:3.11
WORKDIR /node
COPY ./requirements.txt /node/requirements.txt
RUN pip install -r requirements.txt
ENV PYTHONPATH=/node
CMD ["python", "main.py"]
