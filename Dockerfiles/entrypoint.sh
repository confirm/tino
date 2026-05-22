#!/bin/sh
set -e

exec gunicorn "$@"
