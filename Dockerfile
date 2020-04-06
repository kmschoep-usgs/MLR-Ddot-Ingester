FROM python:3.6-alpine as build

ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt

# Add build dependencies (See: https://github.com/gliderlabs/docker-alpine/issues/458)
RUN apk add -U --no-cache gcc build-base linux-headers ca-certificates python3-dev libffi-dev openssl-dev py3-virtualenv

RUN if getent ahosts "sslhelp.doi.net" > /dev/null 2>&1; then \
                wget 'https://s3-us-west-2.amazonaws.com/prod-owi-resources/resources/InstallFiles/SSL/DOIRootCA.cer' -O /usr/local/share/ca-certificates/DOIRootCA2.crt && \
                update-ca-certificates; \
        fi

COPY --chown=1000:1000 requirements.txt /build/requirements.txt

WORKDIR /build

RUN virtualenv --python=python3.6 env
RUN env/bin/pip install -r requirements.txt && env/bin/pip install wheel

COPY --chown=1000:1000 README.md /build/README.md
COPY --chown=1000:1000 *.py /build/
COPY --chown=1000:1000 tests /build/tests

RUN env/bin/python -m unittest && env/bin/python setup.py bdist_wheel

FROM artifactory.wma.chs.usgs.gov/wma-docker/mlr/mlr-python-base:latest
LABEL maintainer="gs-w_eto_eb_federal_employees@usgs.gov"

ENV listening_port=6028
ENV protocol=https
ENV oauth_server_token_key_url=https://test.gov/oauth/token_key
ENV authorized_roles=test_default
ENV artifact_id=usgs-wma-mlr-ddot-ingester

COPY --chown=1000:1000 --from=build /build/dist/*.whl .

RUN pip3 install --no-cache-dir --quiet --user ./*.whl

HEALTHCHECK CMD curl -k ${protocol}://127.0.0.1:${listening_port}/version | grep -q "\"artifact\": \"${artifact_id}\"" || exit 1
