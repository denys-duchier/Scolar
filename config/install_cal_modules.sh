#!/bin/bash

# Install module(s) for calendars
# (if already installed, do nothing)


# Test if installed
# (NB: don't launch python, to be faster and also to avoid import bug zope vs pytz)

if [ ! -e /opt/zope213/lib/python2.7/site-packages/icalendar ]
then
 echo "Installing icalendar"
 /opt/zope213/bin/pip install icalendar
fi



