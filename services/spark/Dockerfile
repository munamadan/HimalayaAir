FROM spark:3.5.8-python3

USER root
WORKDIR /app

COPY requirements.txt /tmp/himalayaair-requirements.txt
RUN pip install --no-cache-dir -r /tmp/himalayaair-requirements.txt

COPY scripts /app/scripts
COPY services /app/services
COPY shared /app/shared

ENV PYTHONPATH=/app
ENV PYSPARK_PYTHON=python3

USER 1001
