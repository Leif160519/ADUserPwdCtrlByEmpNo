FROM faucet/python3:latest

LABEL maintainer="yzluofei@126.com"

RUN mkdir /root/.pip

RUN echo "[global]" >> /root/.pip/pip.conf && \
    echo "index-url = http://mirrors.aliyun.com/pypi/simple/" >> /root/.pip/pip.conf && \
    echo "[install]" >> /root/.pip/pip.conf && \
    echo "trusted-host=mirrors.aliyun.com" >> /root/.pip/pip.conf

RUN pip3 install pip --upgrade && pip3 install flask ldap3

RUN mkdir /app
COPY ad-operations.py /app
COPY templates /app/templates

WORKDIR /app

EXPOSE 5000

CMD ["python3", "/app/ad-operations.py"]
