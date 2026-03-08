FROM bitnami/spark:3.5

USER root

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/app/streaming

COPY requirements.txt ./

RUN install_packages python3-pip \
    && pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir -r requirements.txt

COPY src ./src

ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3
ENV SPARK_EXTRA_CLASSPATH=/opt/bitnami/spark/jars/*
ENV PYTHONPATH=/opt/app/streaming/src

CMD ["spark-submit", "--master", "spark://spark-master:7077", "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.2", "src/main.py"]