# ===============================================================================
# FILE: InputProcessor #
# USAGE: #
# DESCRIPTION:
# OPTIONS: 
# REQUIREMENTS: Parse XKMS request from P10 bulk request file
# BUGS: ---
# NOTES: --- 
# AUTHOR: Stuart Wilson 
# COMPANY: --- 
# VERSION: 1.1
# CREATED: 27-Jan-2016 11:30:40 CET
# REVISION: --- 
# ===============================================================================

import etree.ElementTree as ET
from StringIO import StringIO
from xml.dom import minidom
from xml.dom.minidom import Node
import sys, getopt, re, time
from datetime import date
import logging

parseInputFile = False
createXMLFile = False
inputFile = ''
outputFile = ''
bulk_id = 0
buc_id = ''
adminCert = ''
batchTime = ''
#Set batch size to 1000 by default
batchSize = 1000

# Log file of actions
logFile=''


# Read command line args
try:
    myopts, args = getopt.getopt(sys.argv[1:], "pi:l:s:b:x:c:t:o:")
except getopt.GetoptError as e:
    print(str(e))
    print("Usage: %s -p -i <input_file> -l <logfile> -s <batchSize> OR %s -b <bulk_id> -x <buc_id> -c <adminCert> -t <batchTime> -o <output_file>" %
          sys.argv[0] % sys.argv[0])
    sys.exit(2)

# 0==Option, a==argument passed to o
for o, a in myopts:
    if o == '-p':
        parseInputFile = True
    if o == '-i':
        inputFile = a
    if o == '-l':
        logFile = a
    if o == '-s':
        batchSize = a
    if o == '-c':
        adminCertFile = a
        f = open(adminCertFile, 'r')
        adminCert = f.read()
        adminCert = adminCert.rstrip('\r\n')
    if o == '-b':
        bulk_id = a
    if o == '-x':
        buc_id = a
    if o == '-t':
        batchTime = a
    elif o == '-o':
        createXMLFile = True
        outputFile = a


# Set up Namespaces
ET.register_namespace('xbulk', "http://www.w3.org/2002/03/xkms-xbulk")
ET.register_namespace('ogcm', 'http://xkms.ubizen.com/kitoshi')
ET.register_namespace('xkms', 'http://www.xkms.org/schema/xkms-2001-01-20')
ET.register_namespace("ds", "http://www.w3.org/2000/09/xmldsig#")


# Set up log level
# Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
logging.basicConfig(filename=logFile,format='%(asctime)s %(message)s',level=logging.INFO)

def countOccurrence(reqFile, desired):
    try:
        hit_count = 0
        with open(reqFile) as f:
            for line in f:
                if re.match('-----BEGIN CERTIFICATE REQUEST-----', line):
                    hit_count = hit_count + 1
        return hit_count
    except IOError as e:
        logging.exception('IOError')
        logging.error("Exit on Error: %s: exiting", sys.exc_info()[1])
        sys.exit(1)
    except:
        logging.exception('Unexpected Exception in countOccurrence')
        logging.error("Exit on Error: %s: exiting", sys.exc_info()[1])
        sys.exit(1)


def buildPKCS10XKMSReq(reqFile, xkmsReqOutput):
    try:
        logging.debug(' Begin buildPKCS10XKMSReq')
        numberOfRequests = str(countOccurrence(reqFile, '-----BEGIN CERTIFICATE REQUEST-----'))
        #Identify if numberOfRequests is greater than chunk size
        if int(numberOfRequests) > int(batchSize):
            logging.info('  Creating Multiple Chunks')
            # date=time.strftime("%Y-%m-%dT%H:%M:%S")
            date = batchTime
            #1. Calculate number of chunks to create
            numberOfChunks = (int(numberOfRequests)/int(batchSize)) + (int(numberOfRequests)%int(batchSize)> 0)
            logging.info('  BatchTime = %s',batchTime)
            logging.info('  Number of Requests = %s',numberOfRequests)
            logging.info('  Number of Chunks = %s',numberOfChunks)

            #2. Main section - build pkcs10 requests
            REQFILEHANDLE = open(reqFile, "r")
            flag = 1
            pkcs10Line = ''
            reqBody = ''
            reqCounter = 0
            counter = 0
            chunks = 1
            for line in REQFILEHANDLE:
                if line.startswith("-----BEGIN CERTIFICATE REQUEST-----"):
                    flag = 0
                    pkcs10Line = ''
                if line.startswith("-----END CERTIFICATE REQUEST-----"):
                    flag = 1
                    # Found Full Certificate Request so Create XKMS Request
                    # print pkcs10Line
                    reqBody = reqBody + buildXKMSReq(str(reqCounter), str(buc_id), pkcs10Line)
                    counter += 1
                    reqCounter +=1
                if not flag and not line.startswith("-----BEGIN CERTIFICATE REQUEST-----"):
                    newline = line.rstrip('\r\n')
                    pkcs10Line = pkcs10Line + newline
                #Reached point where we have to create an output file either because:
                #a. The number of csr's has reached the batch size specified OR
                #b. We have reached the end of the input file
                if (int(counter) == int(batchSize)) or (int(reqCounter) == int(numberOfRequests)):
                    # 1. Build header for xml output - set bulk_id
                    chunkBulk_id = bulk_id + '_' + str(chunks)
                    header = buildXKMSHeader(chunkBulk_id, date, str(counter))

                    # 2. Build Request Header
                    reqHeader = buildXKMSReqHeader(str(counter))
                    xkmsReqOutputString = header + reqHeader + reqBody + buildXKMSReqFooter() + buildXKMSSignedPart(adminCert)

                    namespaces = {
                    'xbulk': 'http://www.w3.org/2002/03/xkms-xbulk',
                    'xkms': 'http://www.xkms.org/schema/xkms-2001-01-20',
                    'ds': 'http://www.w3.org/2000/09/xmldsig#',
                    }
                    # print xkmsReqOutputString
                    xkmsReq = ET.fromstring(xkmsReqOutputString)
                    xkmsTree = ET.ElementTree(xkmsReq)
                    xkmsReqOutput = 'mcp_bulk_' + str(chunkBulk_id)
                    logging.info('  Creating file: %s', xkmsReqOutput)
                    xkmsTree.write(xkmsReqOutput, encoding="us-ascii", xml_declaration=True)
                    chunks += 1
                    #reset counter
                    counter = 0
                    #reset pkcsLine and reqBody
                    reqBody = ''
                    pkcs10Line = ''
                    # print ET.tostring(xkmsReq)
            REQFILEHANDLE.close()
        else:
            logging.info('Creating Single Chunk')
            # date=time.strftime("%Y-%m-%dT%H:%M:%S")
            date = batchTime

            # 1. Build header for xml output
            header = buildXKMSHeader(bulk_id, date, numberOfRequests)

            # 2. Build Request Header
            reqHeader = buildXKMSReqHeader(numberOfRequests)

            # 3. Main section - build pkcs10 requests


            REQFILEHANDLE = open(reqFile, "r")
            flag = 1
            pkcs10Line = ''
            reqBody = ''
            counter = 0
            for line in REQFILEHANDLE:
                if line.startswith("-----BEGIN CERTIFICATE REQUEST-----"):
                    flag = 0
                    pkcs10Line = ''
                if line.startswith("-----END CERTIFICATE REQUEST-----"):
                    flag = 1
                    # Found Full Certificate Request so Create XKMS Request
                    # print pkcs10Line
                    reqBody = reqBody + buildXKMSReq(str(counter), str(buc_id), pkcs10Line)
                    counter += 1
                if not flag and not line.startswith("-----BEGIN CERTIFICATE REQUEST-----"):
                    newline = line.rstrip('\r\n')
                    pkcs10Line = pkcs10Line + newline

            xkmsReqOutputString = header + reqHeader + reqBody + buildXKMSReqFooter() + buildXKMSSignedPart(adminCert)
            #Close File Handle
            REQFILEHANDLE.close()

            namespaces = {
            'xbulk': 'http://www.w3.org/2002/03/xkms-xbulk',
            'xkms': 'http://www.xkms.org/schema/xkms-2001-01-20',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            }
            # print xkmsReqOutputString
            xkmsReq = ET.fromstring(xkmsReqOutputString)
            xkmsTree = ET.ElementTree(xkmsReq)
            logging.info('  Creating file: %s', xkmsReqOutput)
            xkmsTree.write(xkmsReqOutput, encoding="us-ascii", xml_declaration=True)
            # print ET.tostring(xkmsReq)
        logging.debug(' End buildPKCS10XKMSReq')
    except:
        logging.exception('Unexpected Exception in buildPKCS10XKMSReq')
        logging.error("Exit on Error: %s: exiting", sys.exc_info()[1])
        sys.exit(1)

def buildXKMSHeader(bulk_id, date, numberOfRequests):
    xkmsHeader = '''<?xml version="1.0" encoding="UTF-8"?>
<xbulk:BulkRegister xmlns:xbulk="http://www.w3.org/2002/03/xkms-xbulk"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xkms="http://www.xkms.org/schema/xkms-2001-01-20">
    <xbulk:SignedPart Id="refId_1">
        <xbulk:BatchHeader>
            <xbulk:BatchID>mcp_bulk_''' + bulk_id + '''</xbulk:BatchID>
            <xbulk:BatchTime>''' + date + '''</xbulk:BatchTime>
            <xbulk:NumberOfRequests>''' + numberOfRequests + '''</xbulk:NumberOfRequests>
            <xbulk:ProcessInfo>
                <ogcm:Reason xmlns:ogcm="http://xkms.ubizen.com/kitoshi">some stuff here</ogcm:Reason>
            </xbulk:ProcessInfo>
        </xbulk:BatchHeader>
        <xkms:Respond>
            <xkms:string>KeyName</xkms:string>
            <xkms:string>RetrievalMethod</xkms:string>
            <xkms:string>X509Cert</xkms:string>
        </xkms:Respond>
        '''
    return xkmsHeader


def buildXKMSReqHeader(numberOfRequests):
    xkmsRequestHeader = '''<xbulk:Requests number="''' + numberOfRequests + '''">
    '''
    return xkmsRequestHeader


def buildXKMSReq(keyID, buc_id, pkcs10):
    # 1. Create XKMS Header:
    xkmsRequest = '''
        <xbulk:Request>
                <xkms:Status>Valid</xkms:Status>
                <xkms:KeyID>''' + keyID + '''</xkms:KeyID>
                <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                    <ds:KeyName>http://xkms.ubizen.com/keyname?buc_id=''' + buc_id + '''&amp;</ds:KeyName>
                    <xbulk:PKCS10>''' + pkcs10 + '''</xbulk:PKCS10>
                </ds:KeyInfo>
            </xbulk:Request>
        '''
    return xkmsRequest


def buildXKMSReqFooter():
    xkmsRequestFooter = '''</xbulk:Requests>
        '''
    return xkmsRequestFooter


def buildXKMSSignedPart(adminCert):
    xkmsSignedPart = '''</xbulk:SignedPart>
    <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:SignedInfo>
            <ds:CanonicalizationMethod
                Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315" />
            <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1" />
            <ds:Reference URI="#refId_2">
                <ds:Transforms>
                    <ds:Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315" />
                </ds:Transforms>
                <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" />
                <ds:DigestValue />
            </ds:Reference>
        </ds:SignedInfo>
        <ds:SignatureValue />
        <ds:KeyInfo>
            <ds:X509Data>
                <ds:X509Certificate>''' + adminCert + '''</ds:X509Certificate>
            </ds:X509Data>
        </ds:KeyInfo>
    </ds:Signature>
</xbulk:BulkRegister>'''

    return xkmsSignedPart


namespaces = {
    'xbulk': 'http://www.w3.org/2002/03/xkms-xbulk',
    'xkms': 'http://www.xkms.org/schema/xkms-2001-01-20',
    'ds': 'http://www.w3.org/2000/09/xmldsig#',
}


def testScript():
    # Read Sample Input of pkcs10 request and create XKMS output
    buildPKCS10XKMSReq('../../1800/request/mcp_bulk_1800.csr', '../../1800/mcsp_bulk_1800.xml')
    # Extract Cert from XKMS Response and create response file.
    # parseCertfromXKMS('mcp_bulk_xx_response.xml', 'sampleOutRes.txt')


if parseInputFile:
    # Read Sample Input of pkcs10 request and create XKMS output
    logging.info('Begin parseInputFile')
    buildPKCS10XKMSReq(inputFile, outputFile)
    logging.info('End parseInputFile')
    sys.exit()
