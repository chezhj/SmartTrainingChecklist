#!/bin/bash

NEW_PATH=./checklist_new
CLONE_PATH=./latest
SRC_PATH="$CLONE_PATH/SmartTrainingChecklist"
RELEASE_TAG="your_release_tag_here"

cd ~/domains/vdwaal.net || exit

# Ensure the checklist_new directory exists
mkdir -p "$NEW_PATH"

# Clone the repository into CLONE_PATH with the specified RELEASE_TAG
git clone --branch "$RELEASE_TAG" https://github.com/chezhj/SmartTrainingChecklist.git "$CLONE_PATH"

# Copy the required files and directories from the cloned directory
cp -r "$SRC_PATH/checklist" "$NEW_PATH/"
cp -r "$SRC_PATH/smart_training_checklist" "$NEW_PATH/"
cp "$SRC_PATH/db.sqlite3" "$NEW_PATH/"
cp "$SRC_PATH/passenger_wsgid.py" "$NEW_PATH/"
cp "$SRC_PATH/manage.py" "$NEW_PATH/"
cp "$SRC_PATH/requirements.txt" "$NEW_PATH/"
