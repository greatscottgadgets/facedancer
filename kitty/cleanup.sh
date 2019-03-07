#!/bin/sh
#
# This script is used for development only!
# it will cleanup the kitty repository and nothing else
#
ROOTDIR=`dirname $0`

echo 'Deleting pyc files'
echo find $ROOTDIR -iname '*.pyc' -delete
find $ROOTDIR -iname '*.pyc' -delete

echo 'Deleting kitty logs'
echo find $ROOTDIR -path "*/kittylogs/*" -delete
find $ROOTDIR -path "*/kittylogs/*" -delete
echo find $ROOTDIR -type d -name kittylogs -delete
find $ROOTDIR -type d -name kittylogs -delete

echo 'Deleting temporary directories'
echo find $ROOTDIR -path "*/tmp/*" -delete
find $ROOTDIR -path "*/tmp/*" -delete
echo find $ROOTDIR -type d -name tmp -delete
find $ROOTDIR -type d -name tmp -delete
