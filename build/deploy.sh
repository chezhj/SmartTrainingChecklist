#!/bin/bash +x

#get param from command line
tag="$1"
DOMAIN="fly.vdwaal.net"
APP="fly"
VERSION_FILE="/smart_training_checklist/__init__.py
cd ~/domains/

#Verify directory app_$tag exists
newdir="${APP}_${tag}"

if [ ! -d $newdir ]; then
    echo "Error: directory $newdir does not exist"
    exit 1
fi
#verify version
version="v"$(grep -oP '__version__ = "\K\S+' ${newdir}${VERSION_FILE} | tr -d '"' )
if [ "$version" != "${tag}" ]; then
    echo "Error: directory ${newdir} does not contain version ${tag}"
    exit 1
else 
    echo "Found version, ${tag} in ${newdir}"
fi


# Stop the current application
echo "Stopping the current application..."
output=$(cloudlinux-selector stop --json --interpreter python --app-root domains/${DOMAIN})
#expected = {"result": "success", "timestamp": 1715533882.345499}
# Check if the result is "success"
if [[ "$output" != *"\"result\": \"success\""* ]]; then
    echo "Error: Failed to stop the current application."
    exit 1
fi

cd ~
#get version information from  version file
old_version="v"$(grep -oP '__version__ = "\K\S+' domains/${DOMAIN}/${VERSION_FILE} | tr -d '"' )
echo "Found current version ${old_version}"

#let user confirm continue
echo "Moving ${DOMAIN} to ${APP}_${old_version}"
read -p "Are you sure you want to continue? (y/n) " -n 1 -r answer
if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
   echo
   echo "Aborting"
   exit 1
fi
echo
echo "continueing..."
# Move the old application
echo "Moving the old application..."
mv domains/${DOMAIN} "domains/${APP}_${old_version}"


# Copy the new application
echo "Copying the new application..."
mv "domains/${newdir}" "domains/${DOMAIN}"

# Copy the database
if [ -f "domains/${DOMAIN}/db.sqlite3" ]; then
    echo "Moving existing database to filestamped copy of the database..."
    today=$(date +%Y%m%d%H%M%S) 
    mv "domains/${DOMAIN}/db.sqlite3" "db.sqlite3.$today"
fi
	 
echo "Copying the database..."
cp "domains/${APP}_${old_version}/db.sqlite3" domains/${DOMAIN}

# Activate the virtual environment
echo "Activating the virtual environment..."
source /home/vdwanet/virtualenv/domains/${DOMAIN}/3.8/bin/activate

# Zet virtual gebaseerd op variabelen in htaccess
source ~/domains/parse_env.sh ~/domains/${DOMAIN}/public_html/.htaccess

cd ~/domains/${DOMAIN}

# Migrate the database
echo "Migrating the database..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input


read -p "Do you van to start the server? (y/n) " -n 1 -r answer
if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
   echo
   echo "Aborting"
   exit 1
fi

# Start the server
echo "Starting the server..."
output=$(cloudlinux-selector start --json --interpreter python --app-root domains/${DOMAIN})
# Check if the result is "success"
if [[ "$output" != *"\"result\": \"success\"* ]]; then
    echo "Error: Failed to stop the current application."
    exit 1
fi
