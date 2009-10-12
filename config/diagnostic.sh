#!/bin/bash

# Rassemble informations sur le systeme et l'installation ScoDoc pour 
# faciliter le support a distance.

DEST_ADDRESS=emmanuel.viennet@univ-paris13.fr 

TMP=/tmp/scodoc-$(date +%F-%s)

# needed for uuencode
if [ ! -e /usr/bin/uuencode ]
then
   apt-get install sharutils
fi

mkdir $TMP

# Files to copy:
FILES=/etc/debian_version /etc/apt/sources.list 


echo "ScoDoc diagnostic: informations about your system will be sent to $DEST_ADDRESS"
echo "and left in $TMP"

# copy some Zope logs
copy_log() {
 if [ -e $1 ]
 then
   cp $1 $TMP/scodoc_logs
 fi
}
copy_log /opt/scodoc/instance/log/event.log
copy_log /opt/scodoc/instance/log/event.log.1
copy_log /opt/scodoc/instance/log/notes.log
copy_log /opt/scodoc/instance/log/notes.log.1

# Run some commands:
iptables -L > $TMP/iptables.out
ifconfig > $TMP/ifconfig.out
ps auxww > $TMP/ps.out
df -h > $TMP/df.out
dpkg -l > $TMP/dpkg.lst

(cd /opt/scodoc/instance/Products/ScoDoc; svn status > $TMP/svn.status)
(cd /opt/scodoc/instance/Products/ScoDoc; svn diff > $TMP/svn.diff)

# copy files:
for f in $FILES 
do 
   cp $f $TMP/$(basename $f)
done

# archive all stuff and send it

tar cfz $TMP.tgz $TMP

# Code below found on http://www.zedwood.com/article/103/bash-send-mail-with-an-attachment

#requires: basename,date,md5sum,sed,sendmail,uuencode
function fappend {
    echo "$2">>$1;
}
YYYYMMDD=`date +%Y%m%d`

# CHANGE THESE
TOEMAIL=$DEST_ADDRESS
FREMAIL="scodoc-diagnostic@none.org";
SUBJECT="ScoDoc diagnostic - $YYYYMMDD";
MSGBODY="ScoDoc diagonistic sent by diagnostic.sh";
ATTACHMENT="$TMP.tgz"
MIMETYPE="application/gnutar" #if not sure, use http://www.webmaster-toolkit.com/mime-types.shtml


# DON'T CHANGE ANYTHING BELOW
TMP="/tmp/tmpfil_123"$RANDOM;
BOUNDARY=`date +%s|md5sum`
BOUNDARY=${BOUNDARY:0:32}
FILENAME=`basename $ATTACHMENT`

rm -rf $TMP;
cat $ATTACHMENT|uuencode --base64 $FILENAME>$TMP;
sed -i -e '1,1d' -e '$d' $TMP;#removes first & last lines from $TMP
DATA=`cat $TMP`

rm -rf $TMP;
fappend $TMP "From: $FREMAIL";
fappend $TMP "To: $TOEMAIL";
fappend $TMP "Reply-To: $FREMAIL";
fappend $TMP "Subject: $SUBJECT";
fappend $TMP "Content-Type: multipart/mixed; boundary=\""$BOUNDARY"\"";
fappend $TMP "";
fappend $TMP "This is a MIME formatted message.  If you see this text it means that your";
fappend $TMP "email software does not support MIME formatted messages.";
fappend $TMP "";
fappend $TMP "--$BOUNDARY";
fappend $TMP "Content-Type: text/plain; charset=ISO-8859-1; format=flowed";
fappend $TMP "Content-Transfer-Encoding: 7bit";
fappend $TMP "Content-Disposition: inline";
fappend $TMP "";
fappend $TMP "$MSGBODY";
fappend $TMP "";
fappend $TMP "";
fappend $TMP "--$BOUNDARY";
fappend $TMP "Content-Type: $MIMETYPE; name=\"$FILENAME\"";
fappend $TMP "Content-Transfer-Encoding: base64";
fappend $TMP "Content-Disposition: attachment; filename=\"$FILENAME\";";
fappend $TMP "";
fappend $TMP "$DATA";
fappend $TMP "";
fappend $TMP "";
fappend $TMP "--$BOUNDARY--";
fappend $TMP "";
fappend $TMP "";
#cat $TMP>out.txt
cat $TMP|sendmail -t -f none@example.com;
rm $TMP;

