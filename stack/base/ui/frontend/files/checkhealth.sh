set -e

WGET_COMMON_ARGS="--tries 1 --timeout 2"

## Check health of the frontend

# Basics
echo -n "Checking that 80 is REDIRECTED to 443..."
wget $WGET_COMMON_ARGS --server-response --spider http://frontend-service 2>&1 | grep -q "Location: https://" || (echo "ERROR: port 80 -> 443 redirection doesn't work!" && /bin/false)
echo OK

echo -n "Checking that 443 requires basic auth..."
wget $WGET_COMMON_ARGS --server-response --no-check-certificate --spider http://frontend-service 2>&1 | grep -q "401 Unauthorized" || (echo 'ERROR: HTTPS basic authentication misconfigured! This is a security leak!' && /bin/false)
echo OK

echo -n "Checking that 8090 is NEVER available outside of localhost..."
(wget $WGET_COMMON_ARGS --no-check-certificate frontend-service:8090 || /bin/true) || (echo "ERROR: port 8090 is available" && /bin/false)
echo OK

# Check that proxy redirects work
echo -n "Checking proxypass for turnilo..."
wget $WGET_COMMON_ARGS -O - 127.0.0.1:8090/turnilo 2>&1 | grep -q "class=\"app-container\"" || (echo "ERROR: unable to proxypass to turnilo" && /bin/false)
echo OK

echo -n "Checking proxypass for REST backend... "
wget $WGET_COMMON_ARGS -O - 127.0.0.1:8090/rest/turnilo/dashboards/ > /dev/null 2>&1 || (echo "ERROR: unable to proxypass to backend" && /bin/false)
echo OK
