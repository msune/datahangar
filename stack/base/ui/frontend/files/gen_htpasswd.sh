#!/bin/bash

set -e

USERS_FILE=/tmp/users.yaml
FILE=/etc/nginx/htpasswd/htpasswd

mkdir -p /etc/nginx/htpasswd/

echo -n "Generating ${FILE}... "
echo -n > ${FILE}
yq '.users[] | .name + " " + .password' ${USERS_FILE} | tr -d '"' | while read -r user password; do
    echo "${user}:$(openssl passwd -apr1 "${password}")" >> ${FILE}
done
echo "done"
