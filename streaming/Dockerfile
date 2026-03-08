FROM apache/spark:3.5.2-scala2.12-java17-python3-ubuntu

USER root

WORKDIR /opt/app/streaming

COPY requirements.txt ./

RUN apt-get update \
    && apt-get install -y python3-pip \
    && pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir -r requirements.txt \
    && mkdir -p /tmp/.ivy2 /tmp/spark-local \
    && chmod -R 777 /tmp/.ivy2 /tmp/spark-local \
    && rm -rf /var/lib/apt/lists/*

COPY src/ ./src/

ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3
ENV PYTHONPATH=/opt/app/streaming/src
ENV HOME=/tmp
ENV IVY_HOME=/tmp/.ivy2
ENV SPARK_LOCAL_DIRS=/tmp/spark-local

USER spark