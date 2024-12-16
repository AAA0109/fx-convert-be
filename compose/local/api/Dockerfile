# define an alias for the specific python version used in this file.
FROM docker.io/python:3.12.5-slim-bookworm AS python

# Python build stage
FROM python AS python-build-stage

ARG BUILD_ENVIRONMENT=local

# Install apt packages
RUN apt-get update && apt-get install --no-install-recommends -y \
  # dependencies for building Python packages
  build-essential \
  # psycopg dependencies
  libpq-dev \
  # api dependencies
  gnupg curl tini git  \
  # weasyprint dependencies
  weasyprint


# Requirements are installed here to ensure they will be cached.
COPY ./requirements .

# Copy external wheel files
COPY ./external /external

# Create Python Dependency and Sub-Dependency Wheels.
RUN pip wheel --wheel-dir /usr/src/app/wheels  \
  -r ${BUILD_ENVIRONMENT}.txt


# Python 'run' stage
FROM python AS python-run-stage

ARG BUILD_ENVIRONMENT=local
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUILD_ENV=${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}


# devcontainer dependencies and utils
RUN apt-get update && apt-get install --no-install-recommends -y \
  sudo git bash-completion nano ssh

# Create devcontainer user and add it to sudoers
RUN groupadd --gid 1000 dev-user \
  && useradd --uid 1000 --gid dev-user --shell /bin/bash --create-home dev-user \
  && echo dev-user ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/dev-user \
  && chmod 0440 /etc/sudoers.d/dev-user

# Install required system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
  # psycopg dependencies
  libpq-dev \
  # Translations dependencies
  gettext \
  # api dependencies
  gnupg curl tini git  \
  # weasyprint dependencies
  weasyprint \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*


# All absolute dir copies ignore workdir instruction. All relative dir copies are wrt to the workdir instruction
# copy python dependency wheels from python-build-stage
COPY --from=python-build-stage /usr/src/app/wheels  /wheels/

# use wheels to install python dependencies
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
  && rm -rf /wheels/

COPY ./compose/production/api/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/local/api/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

COPY ./compose/local/api/ide/start /start-ide
RUN sed -i 's/\r$//g' /start-ide
RUN chmod +x /start-ide

COPY ./compose/local/api/celery/worker/start /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker
RUN chmod +x /start-celeryworker

COPY ./compose/local/api/celery/beat/start /start-celerybeat
RUN sed -i 's/\r$//g' /start-celerybeat
RUN chmod +x /start-celerybeat

COPY ./compose/local/api/celery/flower/start /start-flower
RUN sed -i 's/\r$//g' /start-flower
RUN chmod +x /start-flower

COPY ./compose/local/api/oms/payment/start /start-omspayment
RUN sed -i 's/\r$//g' /start-omspayment
RUN chmod +x /start-omspayment

COPY ./compose/local/api/ems/corpay/start /start-emscorpay
RUN sed -i 's/\r$//g' /start-emscorpay
RUN chmod +x /start-emscorpay

COPY ./compose/local/api/ems/rfq/start /start-emsrfq
RUN sed -i 's/\r$//g' /start-emsrfq
RUN chmod +x /start-emsrfq

COPY ./compose/local/api/rfq/collector/start /start-rfqcollector
RUN sed -i 's/\r$//g' /start-rfqcollector
RUN chmod +x /start-rfqcollector


COPY . ${APP_HOME}

ENTRYPOINT ["/entrypoint"]
