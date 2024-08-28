#!/usr/bin/env groovy

def bob = "bob/bob -r \${WORKSPACE}/ci/ruleset.yaml"

pipeline {
    agent {
        node {
            label SLAVE
        }
    }

    stages {
        stage('Prepare workspace') {
            steps {
                sh 'git clean -xdff'
                sh 'git submodule sync'
                sh 'git submodule update --init --recursive'
            }
        }
        stage('Bump Deployment Service version') {
            steps {
                sh "${bob} bump-service-version"
                script {
                    env.IMAGE_VERSION = readFile('artifact.properties').trim()
                }
            }
        }
        stage('Build EIAPaaS Deployment Service image') {
            steps {
                sh "${bob} build-deployment-service"
            }
        }
        stage('Publish EIAPaaS Deployment Service image') {
            steps {
                sh "${bob} publish-deployment-service"
            }
        }
        stage('Push changes to version file') {
            steps {
                sh "${bob} push-changes-to-version-file"
            }
        }
        stage('Archive artifact.properties') {
            steps {
                archiveArtifacts artifacts: 'artifact.properties', onlyIfSuccessful: true
            }
        }
    }
}