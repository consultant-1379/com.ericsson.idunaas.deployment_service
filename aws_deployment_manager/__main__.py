"""The main module for the deployment_manager package."""

from . import aws_deployment_manager

if __name__ == '__main__':
    aws_deployment_manager.cli()
