#=============================================================================== 
# FILE: OutputProcessor #
# USAGE: #
# DESCRIPTION:
# OPTIONS: 
# REQUIREMENTS: Parse XKMS Response and create zip archive with certificates
# BUGS: ---
# NOTES: --- 
# AUTHOR: Stuart Wilson 
# COMPANY: --- 
# VERSION: 1.1
# CREATED: 29-Jan-2016 11:30:40 CET
# REVISION: --- 
#=============================================================================== 

import etree.ElementTree as ET
from StringIO import StringIO
from xml.dom import minidom
from xml.dom.minidom import Node
import sys, getopt, re, time
from datetime import date
from subprocess import Popen, PIPE, STDOUT, call
import os
import logging

date=time.strftime("%Y/%m/%d")

# Log file of actions
logFile=''

# Read command line args
try:
    myopts, args = getopt.getopt(sys.argv[1:], "i:l:g")
except getopt.GetoptError as e:
    print(str(e))
    print("Usage: %s -i <input_file> -g" % sys.argv[0] % sys.argv[0])
    sys.exit(2)
    
    
#0==Option, a==argument passed to o    
for o, a in myopts:

    if o == '-i':
        inputFile=a
    if o == '-l':
        logFile=a
    elif o == '-g':
        generateCertFiles = True
        

ET.register_namespace('xbulk',"http://www.w3.org/2002/03/xkms-xbulk")
#ET.register_namespace('xkms',"http://www.w3.org/2002/03/xkms")
ET.register_namespace('ogcm','http://xkms.ubizen.com/kitoshi')
ET.register_namespace('xkms','http://www.w3.org/2002/03/xkms#')
ET.register_namespace("ds","http://www.w3.org/2000/09/xmldsig#")

# Set up log level
# Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
logging.basicConfig(filename=logFile,format='%(asctime)s %(message)s',level=logging.DEBUG)


def parseCertfromXKMS(inputFile):
    
    try:
        # 1. Parse Input File
        tree = ET.parse(inputFile)
        root = tree.getroot()
        namespaces = {
        'dsig':'http://www.w3.org/2000/09/xmldsig#',
        'xkms': 'http://www.xkms.org/schema/xkms-2001-01-20'
        }
        
        # 2. Open output file
        #RESFILEHANDLE = open(outputFile, "w")
        
        # 3. Iterate over required content and write to files
        
        
        for xkmsAnswer in tree.findall('.//xkms:Answer', namespaces):
            keyID = xkmsAnswer.find('.//xkms:KeyID', namespaces)
            #print keyID.text
            certFile = './Certs/' + keyID.text + '.crt'
            RESFILEHANDLE = open(certFile, "w")
            subjectCert = xkmsAnswer.find('.//dsig:X509Certificate',namespaces)
            #print subjectCert.text
            RESFILEHANDLE.write(subjectCert.text)
            RESFILEHANDLE.close()
            formatPEMCert(certFile)
        return True
    except Exception, err:
        logging.exception('Unhandled Exception in parseCertfromXKMS')
        logging.error("Exit on Error: %s: exiting", sys.exc_info()[1])
        sys.exit(1)
    
# Function to Format xkms certificate to PEM format for Openssl consumption for parsing.
def formatPEMCert(inputFile):
    try:
        logging.debug(' Begin formatPEMCert for %s',inputFile)
        RESFILEHANDLE = open(inputFile, "r")
        cert = RESFILEHANDLE.read()
        RESFILEHANDLE.close()

        pemCert = re.sub("(.{64})", "\\1\n", cert)
        #Create new pem file with Headers and Footers
        newFile = inputFile + ".new"

        NEWFILEHANDLE = open(newFile, "w")
        NEWFILEHANDLE.write("-----BEGIN CERTIFICATE-----\n")
        if pemCert[-1:] == "\n":
            pemCert = pemCert[:-1]
        NEWFILEHANDLE.write(pemCert)
        NEWFILEHANDLE.write("\n-----END CERTIFICATE-----")
        NEWFILEHANDLE.close()
        # Subject will be in form 
        #subject= /C=CN/ST=FuJian/L=Xiamen/O=Yealink Network Technology Co., Ltd./OU=Yealink Equipment/CN=yealink.com/serialNumber=ffffffff-ffff-ffff-fff0-001565000062
        #Extract Serial Number RDN (MAC Address) value from certificate
        subject = extractDetails(newFile)
        #pattern = '(serialNumber\=)(.*-)(.*$|.*/)'
        pattern = '(subject=)(.*serialNumber=)(.*-)(.*$|.*/)'
        m = re.match(pattern,str(subject))
        if m:
            #Remove last char (newline or /)
            if m.group(4):
                newFile1 = m.group(4)[:-1] + ".crt"
                #Make lowercase
                print "newFile: "+newFile1
                newFile2 = "./Certs/" + newFile1.lower()
                print "Rename from "+newFile+" to "+ newFile2
                os.rename(newFile, newFile2)
                logging.info('  Created file: %s',newFile2)
                os.remove(inputFile)
        else:
            logging.error(' Found no subject identifier within %s matching criteria, using keyId for filename',inputFile)
            os.rename(newFile,inputFile)
        #os.rename(inputFile, newFile)
        logging.debug(' End formatPEMCert for %s',inputFile)
    except Exception, e:
        logging.error(' Failed to format %s',inputFile)
        logging.error(" Error: %s: exiting due to exception in formatPEMCert", sys.exc_info()[1])
        return False
    return True

def extractDetails(newFile):
    
        print "Open File: "+newFile
        RESFILEHANDLE = open(newFile, "r")
        try:    
            #1. Extract details from cert using openssl
            print("openssl" + "x509" + "-in" + newFile + "-inform" + "PEM" + "-subject" "-issuer")
            pipe = Popen(["openssl", "x509", "-in", newFile , "-inform", "PEM", "-subject", "-issuer", "-enddate", "-noout"],stdout=PIPE, stderr=PIPE)
            result = pipe.communicate(PIPE)[0]
            logging.debug(' Extracted following details: %s from %s',result,newFile )
        except Exception, e:
            logging.exception('extractDetails Exception raised while processing %s',newFile)
            logging.error("Warning: %s: Exception raised in extractDetails", sys.exc_info()[1])
            return False
    
        return result

    
if generateCertFiles:
    #Create Certificate Files
    logging.info('Begin generateCertFiles for %s',inputFile)
    parseCertfromXKMS(inputFile)
    logging.info('End generateCertFiles for %s',inputFile)
    sys.exit()
