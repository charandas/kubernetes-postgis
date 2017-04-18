import base64
import json
import subprocess

from fabric.decorators import task
from fabric.operations import local

IMAGE_NAME = "tensorflight/postgis"
IMAGE_TAG = "9.6-2.3"
FULL_IMAGE_NAME = "{}:{}".format(IMAGE_NAME, IMAGE_TAG)
CHART_NAME = "tensorflight-postgres"
DB_NAME = "tensorflight"

def _get_password():
    return base64.b64decode(json.loads(subprocess.check_output(
        "kubectl get secret --namespace default {}-postgresql -o json".format(CHART_NAME),
        shell=True))["data"]["postgres-password"]).decode("utf-8")


@task
def build_image():
    local("docker build -t {} .".format(FULL_IMAGE_NAME))


@task
def push_image():
    build_image()
    local("docker push {}".format(FULL_IMAGE_NAME))


@task
def setup_db():
    # Install kubernetes-helm
    local("helm init")
    local("helm install --name {CHART_NAME} \
    --set postgresDatabase=tensorflight,image={IMAGE_NAME},imageTag={IMAGE_TAG} stable/postgresql".format(
        IMAGE_NAME=IMAGE_NAME,
        IMAGE_TAG=IMAGE_TAG,
        CHART_NAME=CHART_NAME))


@task
def postgres_shell(command=None):
    # Outside of kubernetes: psql -d tensorflight --username=postgres
    if not command:
        command = "psql -U postgres -h {CHART_NAME}-postgresql {DB_NAME}".format(
            DB_NAME=DB_NAME,
            CHART_NAME=CHART_NAME)

    deployment = "{}-postgresql-client".format(CHART_NAME)
    local("kubectl delete deployment {DEPLOYMENT} --ignore-not-found".format(
        DEPLOYMENT=deployment))

    local("""kubectl run {DEPLOYMENT} --rm --tty -i --image {FULL_IMAGE_NAME} \
    --env "PGPASSWORD={PASS}" \
    --command -- {COMMAND}
    """.format(
        FULL_IMAGE_NAME=FULL_IMAGE_NAME,
        PASS=_get_password(),
        DEPLOYMENT=deployment,
        COMMAND=command))


@task
def print_alchemy_connection_string():
    print("Sql alchemy connection string. Note that each cluster will have different password:\n")
    address = "{}-postgresql.default.svc.cluster.local".format(CHART_NAME)
    print("postgresql+psycopg2://postgres:{PASSWORD}@{ADDRESS}/{DB_NAME}".format(
          PASSWORD=_get_password(),
          ADDRESS=address,
          DB_NAME=DB_NAME))
