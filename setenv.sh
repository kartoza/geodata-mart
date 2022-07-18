#!/usr/bin/env bash

# Show env vars
grep -v '^#' .env

# Export env vars
export $(grep -v '^#' .env | xargs)

# Load env vars with:
# source setenv.sh
# Test:
# echo "${FIRST_NAME}"

export DATABASE_URL=postgres://${POSTGRES_USER}:${POSTGRES_PASS}@${POSTGRES_HOST}:${POSTGRES_SERVICE_PORT}/${POSTGRES_DB}
export CELERY_BROKER_URL="${REDIS_URL}"
