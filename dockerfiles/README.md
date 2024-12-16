# How to build Docker images?

|  Docker   | Versions      |
|---------- |:-------------:|
| Version   | 4.1.1         |
| Engine    | 20.10.8       |
| compose   | 1.29.2        |


# Build (locally)

### Build and run Dashboard docker container
```sh
docker build --tag gcr.io/<PROJECT_ID>/pangea-dashboard:latest --file dockerfiles/Dockerfile__Dashboard .
docker run --env-file <ENV_FILE> gcr.io/<PROJECT_ID>/pangea-dashboard:latest
```

If you are using a Macbook Pro `DB_HOSTNAME=host.docker.internal`


### Examples with PROJECT_ID=pangea-development

#### Run the Cloud Proxy
```sh
# arq-ml-2021
./cloud_sql_proxy -instances=arq-ml-2021:us-east1:dev-thd-ml-psql-db=tcp:5432

# pangea-development
./cloud_sql_proxy -instances=pangea-development:us-central1:pangea-development-postgresql-instance=tcp:5432
```

#### Restore the DB from back up
```sh
# psql connect
psql -h 127.0.0.1 -U dashboard-dev-pangea-io-psql-user -d dashboard-dev-pangea-io-psql-db

# restore the db back-up
psql -h 127.0.0.1 -U dashboard-dev-pangea-io-psql-user -d dashboard-dev-pangea-io-psql-db < sql_2022-09-06-00--dev-pangea-db```
```

#### Docker Build, Run or Push
```sh
# build locally
docker build --tag gcr.io/pangea-development/pangea-dashboard:latest --file dockerfiles/Dockerfile__Dashboard .

# run locally
docker run --env-file .env --net=host gcr.io/pangea-development/pangea-dashboard:latest gunicorn main.wsgi:application

# push local docker image to google cloud
docker push gcr.io/pangea-development/pangea-dashboard:latest
```

#### Docker Run with NewRelic
```sh
docker run --env-file .env --net=host gcr.io/pangea-development/pangea-dashboard:latest newrelic-admin run-program gunicorn main.wsgi:application
```

# Google Cloud Build

## How to login gcloud on local terminal?
```sh
gcloud auth login
```

## How to submit a build to Google Cloud Build?
```sh
PROJECT_ID=<PROJECT_ID> DJANGO_SETTINGS_MODULE=main.settings.<SETTINGS> gcloud builds submit --timeout=0h10m0s .
```

### Example
```sh
PROJECT_ID=pangea-development DJANGO_SETTINGS_MODULE=main.settings.production gcloud builds submit --timeout=0h10m0s .
```
