FROM python:3.11
WORKDIR /node
COPY requirements.txt .
RUN pip install -r requirements.txt
ENV PYTHONPATH=/
CMD ["python", "main.py"]