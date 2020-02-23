ARG RELEASE=2-alpine
ARG TRAC_HACKS_REV=17677
FROM python:$RELEASE

LABEL maintainer="docker@fastprotect.net"

ENV container=docker
ENV LANG=C.UTF-8

RUN apk add --update-cache libxslt graphviz git && \
    pip install gunicorn Trac && \
    rm -rf /root/.cache/ && \
    adduser -S -s /bin/sh trac

ADD *.whl /tmp/
RUN pip install /tmp/*.whl

ADD trac-ini /bin/
ADD start_trac.sh trac_wsgi.py /home/trac/

EXPOSE 8000
CMD ["/bin/sh", "/home/trac/start_trac.sh"]
