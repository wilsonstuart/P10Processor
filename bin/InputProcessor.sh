#!/bin/bash
#=============================================================================== 
# FILE: InputProcessor.sh #
# USAGE: Called by BulkProcessor#
# DESCRIPTION:
# 1. Calculates how many certificates are required by the submitted bulk request file
# 2. Generate XKMS request files
# 3.
# OPTIONS: 
# REQUIREMENTS: Create XKMS request from P10 bulk request file
# Direcotries:
#   /opt/bulkprocessorclient/Custom/ProcessP10/conf/
#   /opt/bulkprocessorclient/Custom/ProcessP10/bin/
# BUGS: ---
# NOTES: --- 
# AUTHOR: Stuart Wilson 
# COMPANY: --- 
# VERSION: 1.1
# CREATED: 27-Jan-2016 11:30:40 CET
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
LOGFILE=InputProcessor_$FILESUFFIX.log

# Obtain Input variables for Processing
BULK_ID=`echo $(grep "BULK_REQUEST_ID=" params.ini ) |  sed -e 's/\\r//g;s/BULK_REQUEST_ID=//g'`
INPUT_FILE=`echo $(grep "bulk_request_filepath=" params.ini ) |  sed -e 's/\\r//g;s/bulk_request_filepath=//g'`
ADMIN_CERT=admin.cert
XKMS_BATCHTIME=`date +%Y-%m-%d"T"%H:%M:%S`


#---------- # Functions #----------
# Function to find exit error from Python Script
func_find_error()
{
    error_string=$(grep "Exit on Error:" $1 )
    #Following syntax deletes the longest match of "Exit on Error:" from front of $error_string
    leftString=${error_string##*"Exit on Error:"}
    #Following syntax deletes the shortest match of ": exiting" from back of $string
    finalString=${leftString%": exiting"*}

    echo "ERROR_MESSAGE=$finalString" >> params.ini

}

# Function to log error messages
func_log_if_error() {
    #Get result of last command (0=success)
    result=${PIPESTATUS[0]}
    if [ "$result" != "0" ]; then
        echo "log_if_error :"$1 | tee -a $LOGFILE
        echo "ERROR_MESSAGE="$1  >> params.ini
        exit 1;
    fi

}

# Function to log activity
func_log() {

		echo "`date '+%Y-%m-%d %H:%M:%S'`	: $1" | tee -a $LOGFILE

}



#Function to create the directories used in processing
func_create_dirs() {

    if [ ! -d "request" ]; then
        mkdir request
        func_log_if_error "mkdir request failed"
    fi

    if [ ! -d "unzip" ]; then
        mkdir unzip
        func_log_if_error "mkdir unzip failed"
    fi

    if [ ! -d "keys" ]; then
        mkdir keys
        func_log_if_error "mkdir keys failed"
    fi

    if [ ! -d "Certs" ]; then
        mkdir Certs/
        func_log_if_error "mkdir Certs failed"
    fi
    func_log "Created directory structure"
    return 0;
}

#Function to create a request file for updating with new parameters that will finally be copied into params.ini
func_make_config_file() {
    xkms_bulk_request_id=`echo $(grep "BULK_REQUEST_ID=" params.ini ) |  sed -e 's/\\r//g;s/BULK_REQUEST_ID=//g'`
    cat $CONF_DIR/$CONFIG_FILE > request_config.txt
    func_log_if_error " make config file failed"
    echo "xkms_bulk_request_id="$xkms_bulk_request_id >> request_config.txt
    func_log_if_error " make config file failed."
    func_log "Config File created"
}



# This is the function that creates the XKMS request
# Calls python script to generate xkms request using input file which contain CSR's
func_create_request() {

# Call python script

OUTPUT_FILE=`dirname $INPUT_FILE`/mcp_bulk_$BULK_ID.xml
func_log "Running InputProcessor.py"
func_log "python InputProcessor.py -p -i $INPUT_FILE -l $LOGFILE -s $BATCH_SIZE -b $BULK_ID -x $BUC_ID -c $ADMIN_CERT -t $XKMS_BATCHTIME -o $OUTPUT_FILE"
python $BIN_DIR/InputProcessor.py -p -i $INPUT_FILE -l $LOGFILE -s $BATCH_SIZE -b $BULK_ID -x $BUC_ID -c $ADMIN_CERT -t $XKMS_BATCHTIME -o $OUTPUT_FILE
result=${PIPESTATUS[0]}
    if [ "$result" != "0" ]; then
        func_find_error $LOGFILE
        exit 1;
    fi

}

#---------- # Begin Main #----------


func_log "Begin Processing input file: $INPUT_FILE"
# 1. Check Directories Exist and make them if they don't
func_create_dirs


# 2. Make Config File

func_make_config_file


# Obtain Extra Variables from config file
BATCH_SIZE=`echo $(grep "batch_size=" request_config.txt ) |  sed -e 's/\\r//g;s/batch_size=//g'`
BUC_ID=`echo $(grep "buc_id=" request_config.txt ) |  sed -e 's/\\r//g;s/buc_id=//g'`

# 3. Validate input File
# Check number of requests in the file
XKMS_NUMBEROFREQUESTS=`grep -c "\-\-\-\-\-BEGIN CERTIFICATE REQUEST\-\-\-\-\-" $INPUT_FILE`
func_log "Number of Requests in Input File: $XKMS_NUMBEROFREQUESTS"
if [ $XKMS_NUMBEROFREQUESTS -gt $BATCH_SIZE ]; then
    #Calculate the number of batches
    func_log  "Num of Requests = $XKMS_NUMBEROFREQUESTS and Batch Size = $BATCH_SIZE"
    NUMBER_OF_CHUNKS=$(( ($XKMS_NUMBEROFREQUESTS + ($XKMS_NUMBEROFREQUESTS - 1)) / $BATCH_SIZE))

else
    NUMBER_OF_CHUNKS=1

fi


# 4. Create XKMS Request File/s

func_create_request


# 5. Update params.ini and exit process returning control to Bulk Processor
# Add :
# xkms_batchid - should be mcp_bulk_<BULK_REQUEST_ID>
# xkms_batchtime - Should be the same for every chunk in the multi-request
# number_of_chunks - number of bulk request files
# xkms_numberofrequests - indicates the total number of requests
# batch_size - maximum number of requests per chunk

echo "xkms_batchid=mcp_bulk_$BULK_ID" >> params.ini
echo "xkms_batchtime=$XKMS_BATCHTIME" >> params.ini
echo "number_of_chunks=$NUMBER_OF_CHUNKS" >> params.ini
echo "xkms_numberofrequests=$XKMS_NUMBEROFREQUESTS" >> params.ini
echo "batch_size=$BATCH_SIZE" >> params.ini



# 6 Exit code if successful should be 0
func_log "End Processing input file: $INPUT_FILE"
exit 0
