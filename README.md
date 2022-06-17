# Geodata Mart

Search, select, clip, and deliver spatial data sources.

## Run

The development stack is managed with Docker Compose.

Spin up development environment

```bash
docker compose up -d
```

Bring down the stack

```bash
docker compose down -v
```

## Deploy

Deployment is expected to be completed with Kubernetes.

## Development

Development and stack is managed using docker. Note that their are multiple "environments" for the application development, including:

- Local development environment: This is a python environment that includes prerequisites such as precommit, black, and other linting/ testing/ code quality tools. This can be the system environment, but using a venv is recommended.
- Development environment: The requirements dev.txt is used by the dev Dockerfile, which is a Django environment with a number of development and debug tools. This is the docker-compose stack environment used for development
- Production environment: The requirements production.txt is used by the production Dockerfile, which is a Django environment intended to be pushed to a container repository, and deployed with kubernetes.

### Prerequisites

Git
precommit
editorconfig
python 3.10

### Dev environment venv creation

```bash
python -m venv venv
venv/bin/activate
python -m pip install -e .[dev]
```

### Framework

This application was modified from cookiecutter-django, and the [project docs](https://cookiecutter-django.readthedocs.io/en/latest/) may be helpful to developers.

### Running commands

Because the django app is run within an isolated docker container and may not have access to the declared environment variables for the project, to run commands it is required to run a temporary instance of the django container. This will initiate the environment variable with the docker entrypoint (rather than a typical command operation), e.g.

```bash
$ docker compose run --rm django python manage.py migrate
$ docker compose run --rm django python manage.py createsuperuser
```

The [docs](https://cookiecutter-django.readthedocs.io/en/latest/developing-locally-docker.html#execute-management-commands) have more information on this process. Note that trying to exec into a running django instance will require you to declare relevant environment variables, e.g.:

- https://github.com/cookiecutter/cookiecutter-django/issues/2821
- https://github.com/cookiecutter/cookiecutter-django/issues/2589

### To do

Integrate https://github.com/jrief/django-sass-processor
