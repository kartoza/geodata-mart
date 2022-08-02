# ARG PYTHON_VERSION=3.9-slim-bullseye

# # define an alias for the specfic python version used in this file.
# FROM python:${PYTHON_VERSION} as python

FROM qgis/qgis:final-3_22_8 as python
# FROM qgis/qgis:final-3_26_1 as python

# Alias the python command with the interpreter used with qgis
# note RUN alias python="/usr/bin/python3" will not work between build steps
# https://github.com/docker-library/python/blob/master/Dockerfile-linux.template#L278
# https://stackoverflow.com/questions/60383262/setting-alias-in-dockerfile-not-working-command-not-found#60383287
RUN cd "$(dirname $(which python3))" \
  && ln -s python3 python \
  && ln -s python3-config python-config

# Python build stage
FROM python as python-build-stage

ARG BUILD_ENVIRONMENT=dev

# Install apt packages
RUN apt-get update && apt-get install --no-install-recommends -y \
  # dependencies for building Python packages
  build-essential \
  # psycopg2 dependencies
  libpq-dev

# Requirements are installed here to ensure they will be cached.
COPY ./requirements .

# Create Python Dependency and Sub-Dependency Wheels.
RUN python -m pip wheel --wheel-dir /usr/src/app/wheels  \
  -r ${BUILD_ENVIRONMENT}.txt


# Python 'run' stage
FROM python as python-run-stage

ARG BUILD_ENVIRONMENT=dev
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV BUILD_ENV ${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

# Install required system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
  # psycopg2 dependencies
  libpq-dev \
  # Translations dependencies
  gettext \
  # install additional app dependencies
  libmagic1 \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# All absolute dir copies ignore workdir instruction. All relative dir copies are wrt to the workdir instruction
# copy python dependency wheels from python-build-stage
COPY --from=python-build-stage /usr/src/app/wheels  /wheels/

# use wheels to install python dependencies
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
  && rm -rf /wheels/

COPY ./docker/production/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./docker/dev/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start


COPY ./docker/dev/celery/worker/start /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker
RUN chmod +x /start-celeryworker

COPY ./docker/dev/celery/beat/start /start-celerybeat
RUN sed -i 's/\r$//g' /start-celerybeat
RUN chmod +x /start-celerybeat

COPY ./docker/dev/celery/flower/start /start-flower
RUN sed -i 's/\r$//g' /start-flower
RUN chmod +x /start-flower


FROM python-run-stage as python-exec-stage

# copy application code to WORKDIR
COPY . ${APP_HOME}

ENTRYPOINT ["/entrypoint"]
