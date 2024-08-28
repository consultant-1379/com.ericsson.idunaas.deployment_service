"""A module to be used to define the packaging of deployment_manager."""
from setuptools import setup, find_packages


setup(
    name='aws_deployment_manager',
    version='0.1.0',
    description='Package to manage IDUN aaS deployments on AWS',
    author='xxxx',
    author_email='xxxx',
    packages=find_packages(exclude=('tests', 'docs')),
    python_requires='>=3.6'
)
