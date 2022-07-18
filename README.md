# Geodata Mart

Search, select, clip, and deliver spatial data sources.

## Run

The development stack is managed with Docker Compose.

Spin up development environment

```bash
docker compose up -d --build
```

Bring down the stack

```bash
docker compose down -v
```

### Running commands

Because the django app is run within an isolated docker container and may not have access to the declared environment variables for the project, from within a container run the provided helper script to configure the environments:

```bash
source /app/setenv.sh &> /dev/null
```

This script will output the values from the .env to the console, so piping to dev/null is recommended. Once this script has run and defined the environment, running django commands may proceed as normal

```bash
python /app/manage.py shell
```

## Deploy

Deployment is expected to be completed with Kubernetes.

## Development

Development and stack is managed using docker. Note that their are multiple "environments" for the application development, including:

- Local development environment: This is a python environment that includes prerequisites such as precommit, black, and other linting/ testing/ code quality tools. This can be the system environment, but using a venv is recommended.
- Development environment: The requirements dev.txt is used by the dev Dockerfile, which is a Django environment with a number of development and debug tools. This is the docker-compose stack environment used for development
- Production environment: The requirements production.txt is used by the production Dockerfile, which is a Django environment intended to be pushed to a container repository, and deployed with kubernetes.

### Prerequisites

Development systems should have:

- git
- precommit
- editorconfig
- python 3.8

### Dev environment venv creation

```bash
python -m venv venv
venv/bin/activate
python -m pip install -e .[dev]
```

### Framework

This application was modified from cookiecutter-django, and the [project docs](https://cookiecutter-django.readthedocs.io/en/latest/) may be helpful to developers.

### Settings

It is desirable to aim for [dev-prod-parity](https://12factor.net/dev-prod-parity). The `production.py` settings exclude many functions from `dev.py`, such as debug and dev tools and a change in email service configuration. The `frontend.py` settings replicate `dev`, but disable white noise and the offline caching of django-compressor to allow more dynamic loading and modification of frontend assets without having to restart the stack.

Note that changes to the celery tasks etc. will require you to rerun the docker build function before your changes are reflected in the tasks and scripts.
