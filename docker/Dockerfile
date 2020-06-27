ARG RELEASE=2-alpine
ARG TRAC_HACKS_REV=17677
FROM python:$RELEASE

LABEL maintainer="docker@fastprotect.net"

ENV container=docker LANG=C.UTF-8
ENV TRAC_VERSION="1.4"

RUN apk add --update-cache libxslt graphviz git && \
    pip install gunicorn Trac>=${TRAC_VERSION} PyMySQL pytz Babel && \
    rm -rf /root/.cache/ && \
    adduser -S -s /bin/sh trac

ADD *.whl /tmp/
RUN pip install /tmp/*.whl && \
    rm /usr/local/bin/trac-manage

ADD trac-* /bin/
ADD start_trac.sh trac_wsgi.py /home/trac/

ENV TRAC_DATABASE="sqlite:db/trac.db" \
    TRAC_BASE_URL="" \
    TRAC_PROJECT_NAME="My Project" \
    TRAC_PROJECT_DESCRIPTION="My New Project" \
    TRAC_PROJECT_ADMIN="no-reply@example.com" \
    TRAC_REPO_DIR="/git"

EXPOSE 8000
CMD ["/bin/sh", "/home/trac/start_trac.sh"]
