import os

from invoke import task

# from conferences.euroscipy2019 import *
# from conferences.euroscipy2019_certificates import *


@task
def docker_build(ctx):
    ctx.run('docker build -t docstamp .')


@task
def docker_launch(ctx):
    ctx.run(f'docker run -d -t --rm -v "{os.path.abspath(os.curdir)}:/app" --name docstamp docstamp:latest')


@task
def docker_run(ctx):
    ctx.run('docker exec -t docstamp sh -c "pipenv run inv all"')
    ctx.run('docker stop docstamp')


@task
def docker_clean(ctx):
    ctx.run('docker rmi docstamp')
