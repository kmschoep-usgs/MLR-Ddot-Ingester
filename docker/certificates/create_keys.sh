#!/bin/bash

# Create wildcard certificates: ./create_keys.sh
# Create certificate with IP alt name: ./create_keys.sh "IP:192.168.99.100"
# Create certificate with DNS alt name: ./create_keys.sh "DNS:workbench.local"
# Create certificate with mixed alt namse: ./create_keys.sh "IP:192.168.99.100,DNS:workbench.local"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
HOSTNAME="${1:-DNS:localhost}"

rm -f $DIR/wildcard* || true

openssl genrsa -out $DIR/wildcard.key 2048
openssl req -nodes -newkey rsa:2048 -keyout $DIR/wildcard.key -out $DIR/wildcard.csr -extensions SAN -reqexts SAN \
    -config <(cat /etc/ssl/openssl.cnf <(printf "\n[SAN]\nkeyUsage = nonRepudiation, digitalSignature, keyEncipherment\nbasicConstraints = CA:FALSE\nsubjectAltName=${HOSTNAME}")) \
    -subj "/C=US/ST=Wisconsin/L=Middleon/O=US Geological Survey/OU=WMA/CN=*"
openssl x509 -req \
  -extfile <(printf "keyUsage = nonRepudiation, digitalSignature, keyEncipherment\nbasicConstraints = CA:FALSE\nsubjectAltName=${HOSTNAME}") \
  -days 9999 -in $DIR/wildcard.csr -signkey $DIR/wildcard.key  -out $DIR/wildcard.crt