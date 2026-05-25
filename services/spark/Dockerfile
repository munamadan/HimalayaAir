FROM spark:3.5.8-python3

USER root
WORKDIR /app

COPY requirements.txt /tmp/himalayaair-requirements.txt
RUN pip install --no-cache-dir -r /tmp/himalayaair-requirements.txt

RUN mkdir -p /tmp/.ivy2 \
    && /opt/spark/bin/spark-submit \
      --conf spark.jars.ivy=/tmp/.ivy2 \
      --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8 \
      --master local[1] \
      --class org.apache.spark.examples.SparkPi \
      /opt/spark/examples/jars/spark-examples_2.12-3.5.8.jar 1 \
    && cp /tmp/.ivy2/jars/*.jar /opt/spark/jars/ \
    && rm -rf /tmp/.ivy2

RUN if ! awk -F: '$3 == 1001 { found = 1 } END { exit !found }' /etc/group; then echo "sparkuser:x:1001:" >> /etc/group; fi \
    && if ! awk -F: '$3 == 1001 { found = 1 } END { exit !found }' /etc/passwd; then echo "sparkuser:x:1001:1001:Spark runtime user:/tmp:/usr/sbin/nologin" >> /etc/passwd; fi

COPY scripts /app/scripts
COPY services /app/services
COPY shared /app/shared

ENV PYTHONPATH=/app
ENV PYSPARK_PYTHON=python3
ENV HOME=/tmp

USER root
