#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SERVICE_NAME=$(basename $SCRIPT_DIR)

if [ ! -f $SCRIPT_DIR/config.ini ]; then
    echo "config.ini file not found. Please make sure it exists. If not created yet, please copy it from config.example."
    exit 1
fi

if [ -f $SCRIPT_DIR/current.log ]; then
    rm $SCRIPT_DIR/current.log*
fi

# set permissions for script files
chmod a+x $SCRIPT_DIR/install.sh
chmod 744 $SCRIPT_DIR/install.sh

chmod a+x $SCRIPT_DIR/restart.sh
chmod 744 $SCRIPT_DIR/restart.sh

chmod a+x $SCRIPT_DIR/uninstall.sh
chmod 744 $SCRIPT_DIR/uninstall.sh

chmod a+x $SCRIPT_DIR/service/run
chmod 755 $SCRIPT_DIR/service/run

chmod a+x $SCRIPT_DIR/service/log/run
chmod 755 $SCRIPT_DIR/service/log/run

# create sym-link to run script in deamon
ln -s $SCRIPT_DIR/service /service/$SERVICE_NAME
# add install-script to rc.local to be ready for firmware update
filename=/data/rc.local
if [ ! -f $filename ]
then
    touch $filename
    chmod 755 $filename
    echo "#!/bin/bash" >> $filename
    echo >> $filename
fi


grep -qxF  || echo "exec multilog t s153600 n2 /var/log/$SERVICE_NAME"
grep -qxF "exec multilog t s153600 n2 /var/log/$SERVICE_NAME" $SCRIPT_DIR/service/log/run || echo exec multilog t s153600 n2 /var/log/$SERVICE_NAME >> $SCRIPT_DIR/service/log/run

grep -qxF "$SCRIPT_DIR/install.sh" $filename || echo "/bin/bash $SCRIPT_DIR/install.sh" >> $filename
