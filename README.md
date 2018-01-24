# P10Processor
Bulk Portal - PKCS10 Processing scripts to issue bulk certificates

Skip to content
This repository
Search
Pull requests
Issues
Marketplace
Explore
 @wilsonstuart
 Sign out
 Unwatch 1
  Star 0  Fork 0 wilsonstuart/P10Processor
 Code  Issues 0  Pull requests 0  Projects 0  Wiki  Insights  Settings
Branch: master Find file Copy pathP10Processor/README.txt
08590c1  just now
@wilsonstuart wilsonstuart Initial commit
1 contributor
RawBlameHistory     
133 lines (72 sloc)  5.03 KB
#####Bulk Scripts to take PEM encoded PKCS10 CSR's and output zip file containing issued certificates####

Input Scripts:
-InputProcessor.sh
-InputProcessor.py

Output Scripts:
-OutputProcessor.sh
-OutputProcessor.py


Template should be concatenated list of CSR's as defined in the template:

prerequisite:
MCS 2.8 has been deployed


Configure Bulk Portal according to documentation.

Note: Ensure that the RA administrators that are created have "Allow invalid Authentication Signature in XKMS"

DB Changes:
Use the details in Create_Workflow_Volte_P10.txt  - standard process work flow, this has no approval required.

Functionality of InputProcessor.sh:
# 1. Check Directories Exist and make them if they don't
# 2. Make Config File
# 3. Validates input File to find out if it should be split into chuncks.
# 4. Create XKMS Request File/s by calling Python script (details below)
# 5. Update params.ini and exit process returning control to Bulk Processor
# 6. Exit code if successful should be 0


InputProcessor.py - called from shell script using python $BIN_DIR/InputProcessor.py -p -i $INPUT_FILE -l $LOGFILE -b $BULK_ID -x $BUC_ID -c $ADMIN_CERT -t $XKMS_BATCHTIME -o $OUTPUT_FILE
# 1. Sets up variables accroding to command line params
# 2. Calls Main Function - buildPKCS10XKMSReq(inputFile,outputFile) - This creates the xkms request files based on the input.


OutputProcessor.sh
# 1. Scan for response files and process them using Python script (details below).
# 2. Obtain Extra Variables from config file
# 3. Validate input File
# 4. Check Certificate numbers match number of requested certificates
# 5. Compress the certificates
# 6. Update params.ini and exit process returning control to Bulk Processor
# 7. Exit code if successful should be 0

OutputProcessor.sh
# 1. Extract certs from XKMS files
# 2. Parse cert using openssl to obtain common name and pem encode it.
# 3. write cert to Certs folder


Troubleshooting:
current behaviour (if a single request fails the entire bulk order fails) could lead to a real headache for operations and the customer.  This is being addressed by MCS-6454/MCS-6452  about the error handling in Bulk and specifically the document https://confluence.vzbi.com/display/PRO/XKMS+Responder . I know we are working on addressing this, but I wanted to find out if there is anything I can do in the scripts to help resolve this in the short term.

If a failure occurs in a batch process - End user wants to know what happened to the requests i.e whats been processed, what fails, what to resubmit etc.

The submitter of the request will have very little information to identify what went wrong with their batch.

If you look at a typical workflow:

1. Init – New Request Identified and folders created

2. Approve – Manual Approval Required

3. getbulkrequest – (Internal) – Obtain request file from RA API

4. EXECUTE Input Script

5. sendrequest – (Internal) – Send xkms request to XKMS Responder

6. wait – (Internal) – Poll database

7. getresponse – (Internal) - obtain file from xkms and store in response directory

8. EXECUTE Output script

9. Publish results – (Internal) – place file on RA API





Problematic areas that I can see:

1.       Execute Input processing – can be controlled from input scripts and reports errors in log files which will output the result to the user based on ERROR_MESSAGE in params.ini

2.       sendRequest failure???

3.       XKMS parsing failures at XKMS Agent???? – I believe this is being addressed by the release

4.       Wait – if wait time is exceeded then user gets error but does not know what happened to certificates??? – Example if there were problems with the CAAPI.

5.       Execute Output Processing – can be controlled from input scripts and reports errors in log files which will output the result to the user based on ERROR_MESSAGE in params.ini



Setting the wait time on the bulk processor.

The bulkprocessor.waitforrequestcompletion.timeout must be set by taking into account the following parameters:

• The number of certificate requests in a bulk request.

• XKMS agent wake up time defined by the property xkmsagent.scheduling.period in the XKMSResponder configuration file (phoenix.properties).

• XKMS Responder processing time: time necessary to parse and process the bulk request.

• Signing Engine processing time: time necessary to process (create all certificates from) the bulk request.

For example, if:

• The number of certificate requests in the bulk request is 100.

• The xkmsagent.scheduling.period is set to 15 minutes.

• The XKMS Responder and Signing Engine processing time for processing 100 requests is less than or equal to 10 minutes.

Then the bulkprocessor.waitforrequestcompletion.timeout is at least 25 minutes.





Testing:

Input Processing
python InputProcessor.py -p -i ../../1800/request/mcp_bulk_1800.csr -b 0 -x 12345678 -c /Development/workspace/Volte/1800/admin.cert -t 090761977 -o mcp_bulk_1800.xml


OutputProcessing:
python OutputProcessor.py -i /Development/workspace/Volte/1800/response/mcp_bulk_1800_response.xml -l outputProcessor.log -g
© 2018 GitHub, Inc.
Terms
Privacy
Security
Status
Help
Contact GitHub
API
Training
Shop
Blog
About
