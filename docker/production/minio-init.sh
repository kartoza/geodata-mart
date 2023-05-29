 #!/bin/sh

set -o errexit
set -o pipefail
set -o nounset

# Check if minio website has been set

until curl --head --silent --fail http://minio:9000/minio/health/live 1> /dev/null 2>&1; do
    sleep 1
done

# Add host

config_file="root/.mc/config.json"

if grep -q "\"${DJANGO_AWS_S3_CUSTOM_DOMAIN}\"" "$config_file" >/dev/null 2>&1; then
    echo "Config file exists"
else
    /usr/bin/mc config host add gdm ${DJANGO_AWS_S3_CUSTOM_DOMAIN} ${DJANGO_AWS_ACCESS_KEY_ID} ${DJANGO_AWS_SECRET_ACCESS_KEY}
fi


# Check if bucket exists or not
if mc ls --recursive --versions gdm/${DJANGO_AWS_STORAGE_BUCKET_NAME} >/dev/null 2>&1; then
    echo "Bucket '${DJANGO_AWS_STORAGE_BUCKET_NAME}' exists."
else
   /usr/bin/mc mb gdm/${DJANGO_AWS_STORAGE_BUCKET_NAME}
fi

# Check if bucket permission has been set

bucket_permission=$(mc anonymous get gdm/${DJANGO_AWS_STORAGE_BUCKET_NAME} | awk '{print $NF}' | tr -d '`')
echo "the bucket bucket_permission is ${bucket_permission}"
if [[ ${bucket_permission} = "download" ]];then
  echo "access correctly set to download"
else
  echo "Set access of  ${DJANGO_AWS_STORAGE_BUCKET_NAME} to download"
  /usr/bin/mc anonymous  set download gdm/${DJANGO_AWS_STORAGE_BUCKET_NAME}
fi


