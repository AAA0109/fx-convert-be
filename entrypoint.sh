#!/bin/bash
set -e

echo '*****************************'
echo '** Starting entrypoint ******'
echo '*****************************'

############################
# Setup bash options
############################
#set -o errexit
#set -o pipefail
#set -o nounset

############################
# TODO: Health checks
############################


############################
# Setup GPG keys from GCS
############################
if [[ "$GPG_KEYS_GET_FROM_GS_BUCKET" -eq "1" ]]; then
    echo '*****************************'
    echo '** Getting GPG Keys *********'
    echo '*****************************'
    gsutil --version
    mkdir -p $GPG_HOME_DIR
    gsutil cp -r $GPG_KEYS_GS_BUCKET_FULL_PATH/* $GPG_HOME_DIR/
    ls -lR $GPG_HOME_DIR
    echo '*****************************'
    echo '**** Finishing GPG Keys *****'
    echo '*****************************'
fi

############################
# Run the default commands
############################
if [[ "$RUN_DAJNGO_COLLECTSTATIC_AND_MIGRATE" -eq "1" ]]; then
    echo '*****************************'
    echo '** Running collectstatic ****'
    echo '*****************************'

    python manage.py collectstatic --noinput
    python manage.py migrate

    echo '*****************************'
    echo '** Finishing collectstatic **'
    echo '*****************************'
fi

############################
# Run unit test
############################
if [[ "$RUN_DAJNGO_TESTS" -eq "1" ]]; then
    echo '*****************************'
    echo '** Running unit tests ****'
    echo '*****************************'

    DJANGO_SETTINGS_MODULE='main.settings.tests' python manage.py test --verbosity 3 --noinput --parallel

    echo '*****************************'
    echo '** Finishing unit tests **'
    echo '*****************************'
fi

############################
# Load the data
############################
#./loaddata.sh

############################
# Run the web server
############################
if [[ "$RUN_THE_WEB_SERVER" -eq "1" ]]; then
    echo '*****************************'
    echo '* Running the web server  ***'
    echo '*****************************'

    # Timeout is set to 0 to disable the timeouts of the workers to allow Cloud Run to handle instance scaling.
    exec daphne -b 0.0.0.0 -p 8000 main.asgi:application

    echo '*****************************'
    echo '* Finishing the web server **'
    echo '*****************************'
fi

echo '*****************************'
echo '** Finishing entrypoint *****'
echo '*****************************'
