**BUILD DOCKER IMAGE**

sudo docker build --force-rm --rm -t com.ericsson.oss.idunaas.deployment.service:{version} .

e.g.
sudo docker build --force-rm --rm -t com.ericsson.oss.idunaas.deployment.service:1.0.0 .

**RUN DOCKER**

sudo docker run --rm -v {path_to_config_folder}:/var/config -e AWS_ACCESS_KEY_ID="{aws_access_key}" -e AWS_SECRET_ACCESS_KEY="{aws_secret_key}" -e AWS_DEFAULT_REGION="{aws_region}" com.ericsson.oss.idunaas.deployment.service:{version}

e.g.
sudo docker run --rm -v /home/qmarjat/IDUN/code/config/:/var/config -e AWS_ACCESS_KEY_ID="AKIAVXMVJUK" -e AWS_SECRET_ACCESS_KEY="YGDzAHvrJ8yST4Sjq982hd9+zyBy2D" -e AWS_DEFAULT_REGION="us-east-1" com.ericsson.oss.idunaas.deployment:1.0


