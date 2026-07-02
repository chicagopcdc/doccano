#!/bin/bash
sudo yum update -y
sudo yum install docker -y
sudo usermod -a -G docker ec2-user
sudo systemctl enable docker.service
sudo systemctl start docker.service
sudo chmod 666 /var/run/docker.sock
sudo yum install -y git
sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
# sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
git clone https://github.com/chicagopcdc/doccano.git
cd doccano/
git checkout -t origin/pcdc_dev

#define parameters which are passed in.
doccano_secrets_str=$(aws secretsmanager get-secret-value --secret-id doccano_creds)
doccano_secrets="$(echo $doccano_secrets_str | jq '.SecretString' | jq '. | fromjson')"
ADMIN_PASSWORD="$(echo $doccano_secrets | jq -r '.ADMIN_PASSWORD')"
RABBITMQ_DEFAULT_PASS="$(echo $doccano_secrets | jq -r '.RABBITMQ_DEFAULT_PASS')"
POSTGRES_PASSWORD="$(echo $doccano_secrets | jq -r '.POSTGRES_PASSWORD')"
FLOWER_BASIC_AUTH="$(echo $doccano_secrets | jq -r '.FLOWER_BASIC_AUTH')"
POSTGRES_HOST="$(echo $doccano_secrets | jq -r '.POSTGRES_HOST')"

ENCODED_POSTGRES_PASSWORD=$(jq -rn --arg pwd $POSTGRES_PASSWORD '$pwd|@uri')


gearbox_secrets_str=$(aws secretsmanager get-secret-value --secret-id gearbox_creds)
gearbox_secrets="$(echo $gearbox_secrets_str | jq '.SecretString' | jq '. | fromjson')"
FENCE_CLIENT_ID="$(echo $gearbox_secrets | jq -r '.FENCE_CLIENT_ID')"
FENCE_CLIENT_SECRET="$(echo $gearbox_secrets | jq -r '.FENCE_CLIENT_SECRET')"
FENCE_TOKEN_URL="$(echo $gearbox_secrets | jq -r '.FENCE_TOKEN_URL')"
GEARBOX_RAW_CRITERIA_URL="$(echo $gearbox_secrets | jq -r '.GEARBOX_RAW_CRITERIA_URL')"


#define the template.
env_file=$(cat  << EOF
# platform settings
ADMIN_USERNAME=admin
ADMIN_PASSWORD='$ADMIN_PASSWORD'
ADMIN_EMAIL=pcdc_root@lists.uchicago.edu

# rabbit mq settings
RABBITMQ_DEFAULT_USER=doccano
RABBITMQ_DEFAULT_PASS='$RABBITMQ_DEFAULT_PASS'

# database settings
POSTGRES_HOST='$POSTGRES_HOST'
POSTGRES_USER=doccano
POSTGRES_PASSWORD='$ENCODED_POSTGRES_PASSWORD'
POSTGRES_DB=postgres

# Flower settings
FLOWER_BASIC_AUTH='$FLOWER_BASIC_AUTH'

# GEARBOx settings
FENCE_CLIENT_ID='$FENCE_CLIENT_ID'
FENCE_CLIENT_SECRET='$FENCE_CLIENT_SECRET'
FENCE_TOKEN_URL='$FENCE_TOKEN_URL'
GEARBOX_RAW_CRITERIA_URL='$GEARBOX_RAW_CRITERIA_URL'
EOF
)
echo "$env_file" > ./.env

# Retrieve the secrets for pulling the containers
quay_secrets=$(aws secretsmanager get-secret-value --secret-id quay_io_creds) 
docker login quay.io -p "$(echo $quay_secrets | jq '.SecretString' | jq '. | fromjson' | jq -r '.password')" -u "$(echo $quay_secrets | jq '.SecretString' | jq '. | fromjson' | jq -r '.user')"
sudo docker-compose -f docker/docker-compose.prod.yml --env-file .env up -d


