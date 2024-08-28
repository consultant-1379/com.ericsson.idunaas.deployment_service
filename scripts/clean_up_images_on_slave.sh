#!/bin/bash

# Excluding grafana image, delete other images not been used on slave.

# Delete dangling images
docker rmi -f $(docker images -f "dangling=true" -q)

# Get all images currently in use excluding grafana
USED_IMAGES_EXCLUDING_GRAFANA=($(docker ps -a --format '{{.Image}}' | sort -u | uniq | grep -iv grafana | awk -F ':' '$2{print $1":"$2}!$2{print $1":latest"}'))

# Get all images excluding grafana
ALL_IMAGES_EXCLUDING_GRAFANA=($(docker images --format '{{.Repository}}:{{.Tag}}' | sort -u | grep -iv grafana))

for image_name in "${ALL_IMAGES_EXCLUDING_GRAFANA[@]}"; do
    UNUSED=true
    for used_image_name in "${USED_IMAGES_EXCLUDING_GRAFANA[@]}"; do
        if [[ "$image_name" == "$used_image_name" ]]; then
            UNUSED=false
        fi
    done
    if [[ "$UNUSED" == true ]]; then
        echo "Deleting image $image_name."
        docker rmi "$image_name"
    fi
done