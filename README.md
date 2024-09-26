<div align="center">
  <img src="https://raw.githubusercontent.com/doccano/doccano/master/docs/images/logo/doccano.png">
</div>

# doccano

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/35ac8625a2bc4eddbff23dbc61bc6abb)](https://www.codacy.com/gh/doccano/doccano/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=doccano/doccano&amp;utm_campaign=Badge_Grade)
[![doccano CI](https://github.com/doccano/doccano/actions/workflows/ci.yml/badge.svg)](https://github.com/doccano/doccano/actions/workflows/ci.yml)

doccano is an open-source text annotation tool for humans. It provides annotation features for text classification, sequence labeling, and sequence to sequence tasks. You can create labeled data for sentiment analysis, named entity recognition, text summarization, and so on. Just create a project, upload data, and start annotating. You can build a dataset in hours.

## Demo

Try the [annotation demo](http://doccano.herokuapp.com).

![Demo image](https://raw.githubusercontent.com/doccano/doccano/master/docs/images/demo/demo.gif)

## Documentation

Read the documentation at <https://doccano.github.io/doccano/>.

## Features

- Collaborative annotation
- Multi-language support
- Mobile support
- Emoji :smile: support
- Dark theme
- RESTful API

## Usage

There are three options to run doccano:

- pip (Python 3.8+)
- Docker
- Docker Compose

### pip

To install doccano, run:

```bash
pip install doccano
```

By default, SQLite 3 is used for the default database. If you want to use PostgreSQL, install the additional dependencies:

```bash
pip install 'doccano[postgresql]'
```

and set the `DATABASE_URL` environment variable according to your PostgreSQL credentials:

```bash
DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}?sslmode=disable"
```

After installation, run the following commands:

```bash
# Initialize database.
doccano init
# Create a super user.
doccano createuser --username admin --password pass
# Start a web server.
doccano webserver --port 8000
```

In another terminal, run the command:

```bash
# Start the task queue to handle file upload/download.
doccano task
```

Go to <http://127.0.0.1:8000/>.

### Docker

As a one-time setup, create a Docker container as follows:

```bash
docker pull doccano/doccano
docker container create --name doccano \
  -e "ADMIN_USERNAME=admin" \
  -e "ADMIN_EMAIL=admin@example.com" \
  -e "ADMIN_PASSWORD=password" \
  -v doccano-db:/data \
  -p 8000:8000 doccano/doccano
```

Next, start doccano by running the container:

```bash
docker container start doccano
```

Go to <http://127.0.0.1:8000/>.

To stop the container, run `docker container stop doccano -t 5`. All data created in the container will persist across restarts.

If you want to use the latest features, specify the `nightly` tag:

```bash
docker pull doccano/doccano:nightly
```

### Docker Compose

You need to install Git and clone the repository:

```bash
git clone https://github.com/doccano/doccano.git
cd doccano
```

_Note for Windows developers:_ Be sure to configure git to correctly handle line endings or you may encounter `status code 127` errors while running the services in future steps. Running with the git config options below will ensure your git directory correctly handles line endings.

```bash
git clone https://github.com/doccano/doccano.git --config core.autocrlf=input
```

Then, create an `.env` file with variables in the following format (see [./docker/.env.example](https://github.com/doccano/doccano/blob/master/docker/.env.example)):

```plain
# platform settings
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password
ADMIN_EMAIL=admin@example.com

# rabbit mq settings
RABBITMQ_DEFAULT_USER=doccano
RABBITMQ_DEFAULT_PASS=doccano

# database settings
POSTGRES_USER=doccano
POSTGRES_PASSWORD=doccano
POSTGRES_DB=doccano
```

After running the following command, access <http://127.0.0.1/>.

```bash
docker-compose -f docker/docker-compose.prod.yml --env-file .env up
```

### One-click Deployment

| Service | Button |
|---------|---|
| AWS[^1]   | [![AWS CloudFormation Launch Stack SVG Button](https://cdn.rawgit.com/buildkite/cloudformation-launch-stack-button-svg/master/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home?#/stacks/new?stackName=doccano&templateURL=https://doccano.s3.amazonaws.com/public/cloudformation/template.aws.yaml)  |
| Heroku  | [![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://dashboard.heroku.com/new?template=https%3A%2F%2Fgithub.com%2Fdoccano%2Fdoccano)  |
<!-- | GCP[^2] | [![GCP Cloud Run PNG Button](https://storage.googleapis.com/gweb-cloudblog-publish/images/run_on_google_cloud.max-300x300.png)](https://console.cloud.google.com/cloudshell/editor?shellonly=true&cloudshell_image=gcr.io/cloudrun/button&cloudshell_git_repo=https://github.com/doccano/doccano.git&cloudshell_git_branch=CloudRunButton)  | -->

> [^1]: (1) EC2 KeyPair cannot be created automatically, so make sure you have an existing EC2 KeyPair in one region. Or [create one yourself](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html#having-ec2-create-your-key-pair). (2) If you want to access doccano via HTTPS in AWS, here is an [instruction](https://github.com/doccano/doccano/wiki/HTTPS-setting-for-doccano-in-AWS).
<!-- > [^2]: Although this is a very cheap option, it is only suitable for very small teams (up to 80 concurrent requests). Read more on [Cloud Run docs](https://cloud.google.com/run/docs/concepts). -->

## FAQ

- [How to create a user](https://doccano.github.io/doccano/faq/#how-to-create-a-user)
- [How to add a user to your project](https://doccano.github.io/doccano/faq/#how-to-add-a-user-to-your-project)
- [How to change the password](https://doccano.github.io/doccano/faq/#how-to-change-the-password)

See the [documentation](https://doccano.github.io/doccano/) for details.

## Contribution

As with any software, doccano is under continuous development. If you have requests for features, please file an issue describing your request. Also, if you want to see work towards a specific feature, feel free to contribute by working towards it. The standard procedure is to fork the repository, add a feature, fix a bug, then file a pull request that your changes are to be merged into the main repository and included in the next release.

Here are some tips might be helpful. [How to Contribute to Doccano Project](https://github.com/doccano/doccano/wiki/How-to-Contribute-to-Doccano-Project)

## Citation

```tex
@misc{doccano,
  title={{doccano}: Text Annotation Tool for Human},
  url={https://github.com/doccano/doccano},
  note={Software available from https://github.com/doccano/doccano},
  author={
    Hiroki Nakayama and
    Takahiro Kubo and
    Junya Kamura and
    Yasufumi Taniguchi and
    Xu Liang},
  year={2018},
}
```

## Contact

For help and feedback, feel free to contact [the author](https://github.com/Hironsan).


## Build your own container
from root dir `doccano/` run 
- `docker build --no-cache --progress=plain --file ./docker/Dockerfile.prod --platform=linux/amd64 -t doccano:be_20240813 ./`
- `docker build --no-cache --progress=plain --file ./docker/Dockerfile.nginx --platform=linux/amd64 -t doccano:fe_20240813 ./`


test:
`docker build --no-cache --progress=plain -t doccano:20230911 ./docker/docker-frontend/  &> build.log`


## Run in Docker compose
from the `/` root forder:
- sudo docker-compose -f docker/docker-compose.prod.yml ps
- sudo docker-compose -f docker/docker-compose.prod.yml up -d
- docker-compose -f docker/docker-compose.prod.yml --env-file .env up (not tried yet)


## CREATE AWS ENVIRONMENT:
Doing this in us-east-1 - Virginia and used the base name `doccano`, so for instance `doccano-vpc`, `doccano-sg` etc etc

- Create Secrets
- Create VPC
- Create Security Group for ALB
- Create Target Group
- Create ALB
- Create RDS
- Populate Secrets needed by the EC2
- Create EC2 instance
- Add instance/s to the target group
- Update SSL Cert and listeners

### Populate Secrets needed by the EC2
- add useful secrets to secrets manager:
  - quay_io_creds (quay.io login creds)
  - doccano_creds (all the information needed in the .env file, mostly doccano and DB credentials)

### Create VPC
Select the following options:
- VPC and more
- pick your CIDR block and name (`doccano-vpc`)
- 2 availbiulity zones, 2 private, 2 public subnets
- only 1 nat gateway (in 1 availability zone. We are going to deploy only in that one zone since this application doesn't need to be fault tollerant and can have some downtime. We create 2 so it will be easier to add eventually a second nat gateway down the line if we decide to.)
- Leave the other options as they are

### Create Security Group for ALB
- `doccano-alb-sg`
- select `doccano-vpc`
- create security group for ALB listen to all from 80 and 443
- Maybe restrict to UChicago IPs for now?

### Create Target Group
- create target group for ALB (type instances, name `doccano-target-group`, protocol 80, http1, health check: /) 
- Create button, add instances later

### Create ALB
- name (`doccano-alb`)
- internet facing
- ipv4
- select `doccano-vpc`
- select the two availability zones and the 2 puvlic subnets for the ALB
- select `doccano-alb-sg` security group as well as the VPC `default` (the default will allow full connectivity between the EC2 and the ALB)
- listeners: listen to 443 (set 80 if you don't have a certificate already and you can update later) and forward to target group created previously (may need to refresh the page for it to show up)
- click on create

### Create RDS psql instance
- psql
- 13.13
- production
- single db
- identifier: `doccano`
- master username: `doccano`
- secrets manager
- t3.small
- 100 Gi
- doccano vpc
- force to create a new DB subnet group
- doccano vpc default sec group
- 

### Create EC2 instance
- name= doccano-ec2-20240813-1, Amazon Linux 2023 AMI, t3.medium
- select key pair
- select doccano VPC, private subnet
- No public IP, existing security group 'default' for the doccano VPC
- 40gb gp3
-  previously created role ec2_secrets_manager_role ( or create it if not created previously. Give EC2 read permission on the secrets manager with policy SecretsManagerReadWrite and trust relationship to EC2, as well as CloudWatchLogsFullAccess to push the docker logs to cloudwatch) as instance profile. 
- update ec2_user_data.sh script
- click on create

### Add instance/s to the target group
and add the ec2 created previously
  - For some reason if the instance is only internal it will now turn healthy in the target group. You can just attach a public IP, wait 2/3 minutes for it to turn healthy and then you can remove the elastic IP. That seems to be solving the issue. (TRY added ALB's security group on port 80 in EC2's security group. By doing this, the issue will be resolved.)

### Update SSL Cert and listeners
- get a cert from certificate manager for the ALB
- update the DNS provider with the CNAME of the ALB
- add certificate to the HTTPS 443 listener in the ALB and point to the target group
- add listener to listen to 80 and redirect (redirect to url) 301 to 443 - Redirect to HTTPS://#{host}:443/#{path}?#{query}

### Deploy new version
- Update the ec2_user_data.sh file with the new tag
- Repeat the step `Create EC2 instance`
- Repeat the step `Add instance/s to the target group`
- Remove old instance from the target group
- Terminate old instance


# Debug psql and install on machine when ssh from bastion host
- sudo dnf search postgresql
- sudo dnf install -y postgresql15