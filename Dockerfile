# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Common Dockerfile for Team Muon's EIAPaaS deployment service
#
# Stages:
#   'python_base'
#       Sets the base OS image and configures Zypper for the later stages
#   'python_base_with_pipenv'
#       Installs Pip and prepares the venv for the later stages
#   'base_with_dev_dependencies'
#       Installs the production and testing dependencies for the precode review image
#   'precode_review'
#       Creates the image used to run the precode review
#   'base_with_prod_dependencies'
#       Prepares and installs the production dependencies for the deployment service image
#   'released_image'
#       Creates the final released image
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# # # # # # # # # # # # # #
# Stage 'python_base'
# # # # # # # # # # # # # #

FROM armdocker.rnd.ericsson.se/proj-ldc/common_base_os/sles:3.55.0-8 AS python_base

# Set the Zypper configuration
RUN zypper ar -C -G -f https://arm.sero.gic.ericsson.se/artifactory/proj-ldc-repo-rpm-local/common_base_os/sles/3.55.0-8 LDC-CBO-SLES
RUN zypper ref -f -r LDC-CBO-SLES
RUN zypper install -y python39
RUN zypper clean --all
RUN find /usr -type d -name  "__pycache__" -exec rm -r {} +

# Some Python packages like Click require a local to be set to work, so we set it here
ENV LC_ALL=en_US.utf-8
ENV LANG=en_US.utf-8

# # # # # # # # # # # # # # # # # #
# Stage 'python_base_with_pipenv'
# # # # # # # # # # # # # # # # # #

FROM python_base AS python_base_with_pipenv

RUN zypper install -y python39-pip ca-certificates-mozilla curl unzip
RUN python3.9 -m pip install --upgrade pip
RUN pip3.9 install pipenv==2022.1.8
# Clean out the Python cache after installing Pip and Python packages
RUN find /usr/ -type d -name  "__pycache__" -exec rm -r {} +
# Store all of the packages in /venv/.venv/
WORKDIR /venv/
COPY Pipfile setup.py /venv/
# Set PIPENV_VENV_IN_PROJECT to true so that venv automatically creates the virtual env in the /venv/.venv/ folder
ENV PIPENV_VENV_IN_PROJECT=1

# # # # # # # # # # # # # # # # # # #
# Stage 'base_with_dev_dependencies'
# # # # # # # # # # # # # # # # # # #

FROM python_base_with_pipenv AS base_with_dev_dependencies

# Install the production and testing/development packages into the venv and check the Pipfile and Pipfile.lock match
# If you need to make the Pipfile and Pipfile.lock match, locally run 'pipenv lock' to regenerate a new Pipfile.lock
WORKDIR /venv/
RUN pipenv install --deploy --dev
# Clean out the Python cache after installing Pip and Python packages
RUN find /usr/ -type d -name  "__pycache__" -exec rm -r {} +
# Add the venv bin folder to the PATH
ENV PATH="/venv/.venv/bin/:${PATH}"

# # # # # # # # # # # # #
# Stage 'precode_review'
# # # # # # # # # # # # #

FROM base_with_dev_dependencies AS precode_review

WORKDIR /venv/aws_deployment_manager
# Copy the aws_deployment_manager code and tests into the image
COPY /aws_deployment_manager /venv/aws_deployment_manager/aws_deployment_manager
COPY /aws_deployment_manager/tests /venv/aws_deployment_manager/tests
# Create directory for the CF infrastructure templates
RUN mkdir /idun
COPY templates/ /idun/templates
RUN chmod -R 777 /idun/
# Copy rules for the various linters
COPY pylintrc pylintrc
COPY .flake8 .flake8
RUN pylint aws_deployment_manager
RUN pylint tests
# Ignore non-zero error codes from flake8 and pep257 for now
# These can be set to break the build in future following some cleanup of the codebase
RUN flake8 . || true
RUN pep257 . || true

# # # # # # # # # # # # # # # # # # # #
# Stage 'base_with_prod_dependencies'
# # # # # # # # # # # # # # # # # # # #

FROM python_base_with_pipenv AS base_with_prod_dependencies

# Store all of the packages under the /venv/.venv/ directory
WORKDIR /venv/
RUN pipenv lock
RUN pipenv install --deploy
RUN pipenv graph
# Clean out the Python cache after installing Pip and Python packages
RUN find /usr/ -type d -name  "__pycache__" -exec rm -r {} +

# Install Git
RUN zypper install -y git-core

# Update the path so that we can call tools like pylint directly
ENV PATH="/venv/.venv/bin/:${PATH}"

# Prepare the Helm binary for copying to the final image
WORKDIR /temp/helm
RUN curl -O https://arm1s11-eiffel052.eiffel.gic.ericsson.se:8443/nexus/service/local/repositories/eo-3pp-foss/content/org/cncf/helm/3.8.1/helm-3.8.1.zip
RUN unzip helm-3.8.1.zip
RUN mv /temp/helm/linux-amd64/helm /usr/bin/helm
RUN helm version
RUN rm -rf /temp/help

# Prepare the Kubectl binary for copying to the final image
WORKDIR /temp/kubectl
RUN curl -sL https://arm1s11-eiffel052.eiffel.gic.ericsson.se:8443/nexus/service/local/repositories/eo-3pp-foss/content/org/cncf/kubernetes/kubectl/1.23.5/kubectl-1.23.5.zip -o kubectl.zip
RUN unzip kubectl.zip
RUN mv /temp/kubectl/kubectl /usr/bin
RUN kubectl
RUN rm -rf /temp/kubectl

# Create directory for the CF infrastructure templates
RUN mkdir /idun
COPY templates/ /idun/templates

# # # # # # # # # # # # # #
# Stage 'released_image'
# # # # # # # # # # # # # #

FROM base_with_prod_dependencies as released_image

# Copy the helm 3 binary into the final image
COPY --from=base_with_prod_dependencies /usr/bin/helm /usr/bin/helm
# Copy the kubectl binary into the final image
COPY --from=base_with_prod_dependencies /usr/bin/kubectl /usr/bin/kubectl
# Copy the virtual environment containing only the required packages, into our virtual environment directory
COPY --from=base_with_prod_dependencies /venv/.venv/ /venv/.venv/
# Copy the deployment_manager code into the image
COPY /aws_deployment_manager/ /venv/aws_deployment_manager/

# Install the AWS CLI
WORKDIR /tmp/awscli
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-2.9.8.zip" -o "awscli.zip"
RUN unzip -q awscli.zip
RUN ./aws/install
RUN rm -f awscli.zip
RUN rm -rf /tmp/awscli
RUN aws --version

WORKDIR /venv/.venv/
# Test the the deployment manager can be called
RUN /venv/.venv/bin/python -m aws_deployment_manager --help

# Set the entrypoint so we can call the deployment manager with 'docker run ${FLAGS} ${IMAGE_ALIAS} ${COMMAND}' syntax
# Where ${COMMAND} is one of those listed in aws_deployment_manager/commands
ENTRYPOINT ["/venv/.venv/bin/python", "-m", "aws_deployment_manager"]