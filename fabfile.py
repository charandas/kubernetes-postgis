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
    local("docker pull {}".format(FULL_IMAGE_NAME))
    local("helm install --name {CHART_NAME} \
    --set postgresDatabase=tensorflight,image={IMAGE_NAME},imageTag={IMAGE_TAG} stable/postgresql".format(
        IMAGE_NAME=IMAGE_NAME,
        IMAGE_TAG=IMAGE_TAG,
        CHART_NAME=CHART_NAME))


@task
def print_alchemy_connection_string():
    print("Sql alchemy connection string. Note that each cluster will have different password:\n")
    address = "{}-postgresql.default.svc.cluster.local".format(CHART_NAME)
    print("postgresql+psycopg2://postgres:{PASSWORD}@{ADDRESS}/{DB_NAME}".format(
          PASSWORD=_get_password(),
          ADDRESS=address,
          DB_NAME=DB_NAME))
