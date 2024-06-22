#!/bin/bash

GITHUB_URL=https://github.com/chezhj/SmartTrainingChecklist.git
DOMAIN="fly.vdwaal.net"
APP="fly"

# Check if the release tag argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <release-tag>"
    echo ""
    echo "Current tags:"
    git ls-remote --tags $GITHUB_URL | gawk '{print substr($2,11)}'
    exit 1
fi

RELEASE_TAG="$1"
NEW_PATH="./${APP}_${RELEASE_TAG}"
SRC_PATH="./${APP}_source_${RELEASE_TAG}"

cd ~/domains/ || exit

# Ensure the checklist_new directory exists
mkdir -p "$NEW_PATH"

# Clone the repository into CLONE_PATH with the specified RELEASE_TAG
git clone --branch "$RELEASE_TAG" "$GITHUB_URL" "$SRC_PATH"

# Copy the required files and directories from the cloned directory
cp -r "$SRC_PATH/checklist" "$NEW_PATH/"
cp -r "$SRC_PATH/smart_training_checklist" "$NEW_PATH/"
cp "$SRC_PATH/db.sqlite3" "$NEW_PATH/"
cp "$SRC_PATH/passenger_wsgi.py" "$NEW_PATH/"
cp "$SRC_PATH/manage.py" "$NEW_PATH/"
cp "$SRC_PATH/requirements.txt" "$NEW_PATH/"

echo "Creating backup of ${DOMAIN}"
tar -czf "${APP}_current.tar.gz" "$DOMAIN/"

cp -r ${DOMAIN}/public_html ${NEW_PATH}/
