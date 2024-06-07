import yaml
from passlib.apache import HtpasswdFile
import os

with open('/tmp/users.yaml', 'r') as file:
    config = yaml.safe_load(file)

htpasswd = HtpasswdFile()

for user in config['users']:
    username = user['name']
    password = user['password']
    htpasswd.set_password(username, password)

htpasswd.save('/etc/nginx/htpasswd/htpasswd')
print("htpasswd file created successfully.")
