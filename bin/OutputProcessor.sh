#!/bin/bash
#=============================================================================== 
# FILE: OutputProcessor.sh #
# USAGE: Called by BulkProcessor#
# DESCRIPTION:
# 1. Generate Certificate files from XKMS Response file
# OPTIONS: 
# REQUIREMENTS:
# Direcotries:/
# BUGS: ---
# NOTES: --- 
# AUTHOR: Stuart Wilson 
# COMPANY: --- 
# VERSION: 1.1
# CREATED: 29-Jan-2016 11:30:40 UTC
# REVISION: --- 
#=============================================================================== 

#---------- # Set up VARIABLES #----------
# Current directory
CURRENT_DIR=`pwd`

# Custom Conf directory
CONF_DIR=/opt/bulkprocessorclient/Volte/P10/conf
BIN_DIR=/opt/bulkprocessorclient/Volte/P10/bin
# Custom Config file
CONFIG_FILE=ProcessP10.conf


FILESUFFIX=$(date '+%Y%m%d%H%M%S')

# Log file of actions
LOGFILE=OutputProcessor_$FILESUFFIX.log

# Obtain Input variables for Processing
BULK_ID=`echo $(grep "BULK_REQUEST_ID=" params.ini ) |  sed -e 's/\\r//g;s/BULK_REQUEST_ID=//g'`
INPUT_FILE=`echo $(grep "bulk_request_filepath=" params.ini ) |  sed -e 's/\\r//g;s/bulk_request_filepath=//g'`
OUTPUT_FILE=`dirname $INPUT_FILE`/mcp_bulk_$BULK_ID.xml
ADMIN_CERT=admin.cert
XKMS_BATCHTIME=`date +%y-%m-%d"T"%H:%M:%S`
#---------- # Functions #----------


func_find_error()
{
    error_string=$(grep "Exit on Error:" $1 )
    leftString=${error_string##*"Exit on Error:"}
    finalString=${leftString%": exiting"*}

    echo "ERROR_MESSAGE=$finalString" >> params.ini

}


func_log_if_error() {

    result=${PIPESTATUS[0]}
    if [ "$result" != "0" ]; then
        echo "log_if_error :"$1
        echo "ERROR_MESSAGE="$1  >> params.ini
        exit 1;
    fi


}


func_log() {

		echo "`date '+%Y-%m-%d %H:%M:%S'`	: $1" | tee -a $LOGFILE
	
}

func_scan_responsefiles() {

for file in `ls ./response/mcp_bulk_$BULK_ID*.xml`
do
#Workaround to fix xkms namespace in xml files
sed -i.bak 's/<xbulk:BulkLocateResult xmlns:xbulk="http:\/\/www.w3.org\/2002\/03\/xkms-xbulk">/<xbulk:BulkLocateResult xmlns:xbulk="http:\/\/www.w3.org\/2002\/03\/xkms-xbulk" xmlns:xkms="http:\/\/www.w3.org\/2002\/03\/xkms#" xmlns:ogcm="http:\/\/xkms.og.ubizen.com\/schema\/xkms-2003-09\/">/g' $file
python $BIN_DIR/OutputProcessor.py -i $file -l $LOGFILE -g
result=${PIPESTATUS[0]}
    if [ "$result" != "0" ]; then
        func_find_error $LOGFILE
        exit 1;
    fi
done

}


#---------- # Begin Main #----------
func_log "Begin Processing"
#1. Scan for response files

func_scan_responsefiles
echo "Python Script finished Processing...."
func_log "Python Script finished Processing...."
# Obtain Extra Variables from config file
BATCH_SIZE=`echo $(grep "batch_size=" request_config.txt ) |  sed -e 's/\\r//g;s/batch_size=//g'`
func_log "BATCH_SIZE=$BATCH_SIZE"
BUC_ID=`echo $(grep "buc_id=" request_config.txt ) |  sed -e 's/\\r//g;s/buc_id=//g'`
# 2. Validate input File
# Check number of requests in the file
XKMS_NUMBEROFREQUESTS=`echo $(grep "xkms_numberofrequests=" params.ini ) |  sed -e 's/\\r//g;s/xkms_numberofrequests=//g'`
func_log "XKMS_NUMBEROFREQUESTS=$XKMS_NUMBEROFREQUESTS"

# 4. Check Certificate numbers match number of requested certificates

NUMBER_OF_CERTIFICATES=`ls ./Certs/*.crt | wc -l`
func_log "NUMBER_OF_CERTIFICATES=$NUMBER_OF_CERTIFICATES"
if [ $XKMS_NUMBEROFREQUESTS -eq $NUMBER_OF_CERTIFICATES ]; then
    #Zip up the Certs directory and upload file
	func_log "About to start zip file processing"
    xkms_bulk_request_id=`echo $(grep "BULK_REQUEST_ID=" params.ini ) |  sed -e 's/\\r//g;s/BULK_REQUEST_ID=//g'`
    publish_result_file="mcp_bulk_"$xkms_bulk_request_id"_response.zip"
    zip -q -r $publish_result_file Certs/
    func_log_if_error  "zip failed"
    result=${PIPESTATUS[0]}

    if [ "$result" = "0" ];
    then
    sed '/publish_result_file=/d' params.ini >  new_params.ini
    full_path=$(ls `pwd`/$publish_result_file | head -1)
    echo "publish_result_file=$full_path" >> new_params.ini
	func_log "Created $full_path"
    mv new_params.ini params.ini
    fi

else
    func_log_if_error  "Mismatch between number of certs and requests"
    exit 1
fi



# 6 Exit code if successful should be 0
func_log "End Processing"
exit 0
