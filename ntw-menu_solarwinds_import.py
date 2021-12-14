#!/usr/bin/env python3

import configparser
import os
import orionsdk
import re
import requests
import sys
import getopt
import smtplib
import socket
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from requests.packages.urllib3.exceptions import InsecureRequestWarning

"""
ntw-menu_solarwinds_import.py - version 1.5.1

This is a script to dinamically import a device list from Solarwinds

Written by Rocco De Angelis
"""

class send_email_SMTP(object):
    """Send text email via SMTP server
    """
    def __init__(self, host, sender_name=None, sender=None, 
    receiver_name=None, receiver=None, subject=None, message=None):
        self.host = host
        self.sender_name = sender_name
        self.sender = sender
        self.receiver_name = receiver_name
        self.receiver = receiver
        self.subject = subject
        self.message = message

    def test(self):
        try:
            smtp_obj = smtplib.SMTP(self.host)
            smtp_test = smtp_obj.ehlo()
            smtp_obj.quit()
            
            if smtp_test[0] == 250:
                #print("Reply Code: " + str(smtp_test[0]) + " OK")
                return True
            else:
                print("Reply Code: " + str(smtp_test[0]) 
                    + " UNKNOWN. (250 is required to continue)\nExiting!")
                return False
        except smtplib.SMTPException as e:
            print("Error: Unable to send email")
            return False
        except socket.error as e:
            print("Error: Could not connect to SMTP server - is it down "
                + "or unreachable?\n({0})".format(e.strerror))
            return False
        except:
            print("Unknown Error: ", sys.exc_info()[0])
            return False

    def send(self):
        mimemsg = MIMEMultipart("alternative")
        mimemsg["Subject"] = self.subject
        mimemsg["From"] = self.sender_name + " <" + self.sender + ">"
        mimemsg["To"] = self.receiver_name + " <" + self.receiver + ">"
        
        html_header = """\
<html style=min-height: 100%; margin: 0;>
  <head></head>
  <bodyi style=min-height: 100%; margin: 0;>
    <p><div style="display: block; font-family: monospace; white-space: pre; font-size: 12px;">"""
        html_body = self.message.replace("\n", "<br>")
        html_trailer = """
   </div></p>
  </body>
</html>
        """
        
        html = html_header + html_body + html_trailer
        #print(html)
        html_msg = MIMEText(html, "html")
        
        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        mimemsg.attach(html_msg)
        
        #try:
        smtpObj = smtplib.SMTP(self.host)
        smtpObj.sendmail(self.sender, self.receiver, mimemsg.as_string())  
        smtpObj.quit()
        #print "Successfully sent email"
        #except SMTPException:
        #   print "Error: unable to send email"

def test_email_server(email_server):
    email = send_email_SMTP(email_server)
    result = email.test()
    return result

def main(nodeRegexArgv):

    config_file = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),"config.ini"
    )
    imported = False

    try:
        config = configparser.ConfigParser()
        config.read(config_file)
        
        #load config files setting
        import_dev_list_file = (config["DATA_PARAMETERS"]
            ["Import_Dev_List_File"])
        enable_email_notification = (config["EMAIL_PARAMETERS"]
            ["EnableEmailNotification"])
        email_on_import = (config["EMAIL_PARAMETERS"]
            ["EmailOnImport"])
        email_on_failure = (config["EMAIL_PARAMETERS"]
            ["EmailOnFailure"])
        sw_host = config["SOLARWINDS_PARAMETERS"]["SW_Host"].split(",")
        sw_username = config["SOLARWINDS_PARAMETERS"]["SW_Username"]
        sw_password = config["SOLARWINDS_PARAMETERS"]["SW_Password"]
        email_server = config["EMAIL_PARAMETERS"]["EmailServer"]
        admin_email_sender_name = (config["EMAIL_PARAMETERS"]
            ["AdminEmailSenderName"])
        admin_email_sender_address = (config["EMAIL_PARAMETERS"]
            ["AdminEmailSenderAddress"])
        admin_email_receiver_name = (config["EMAIL_PARAMETERS"]
            ["AdminEmailReceiverName"])
        admin_email_receiver_address = (config["EMAIL_PARAMETERS"]
            ["AdminEmailReceiverAddress"])
        admin_email_subject = config["EMAIL_PARAMETERS"]["AdminEmailSubject"]
    except:
        print("Error: it is not possible to read config from file: "
            + config_file)
        sys.exit(0)

    def sendmail(em_msg):
        em_host = email_server
        em_sender_name = admin_email_sender_name
        em_sender = admin_email_sender_address
        em_receiver_name = admin_email_receiver_name
        em_receiver = admin_email_receiver_address
        em_subject = admin_email_subject
        email = send_email_SMTP(em_host, em_sender_name, em_sender,
        em_receiver_name, em_receiver, em_subject, em_msg)
        email.send()
        print("e-mail sent to " + admin_email_receiver_address)


    def runNewDevicesList(server_ip):
    
        ip = server_ip
        
        try:
            item_dict = swis.query(
                "SELECT DISTINCT "
                + "NodeID, "
                + "Caption, "
                + "IPAddress, "
                + "Vendor, "
                + "MachineType, "
                + "IOSImage, "
                + "IOSVersion "
                + "FROM Orion.Nodes ORDER BY Caption ASC"
            )
            item_list=item_dict["results"]
            device_entry = headerSpacing
            newDeviceReportMsg = ""
            for item in item_list:
                device_entry += ("{Caption},{IPAddress},,\n".format(**item))
            f = open(import_dev_list_file, "w")
            f.write("#DO NOT EDIT THIS FILE. THIS FILE IS PROCESSED BY "
                + "PYTHON SCRIPT ntw-menu_solarwinds_import.py")
            f.write(device_entry)
            f.close()
            print("ntw-menu device list successfully imported!")
            if len(item_list) > 0:
                device_entry_count = str(len(item_list))
                heading = ("ntw-menu device list import into " 
                    + import_dev_list_file
                    + " has completed successfully.\n")
                count_msg = (device_entry_count
                    + " devices have been re-imported into the"
                    + " ntw-menu. (Manual entries will remain unchanged)")
                device_list_msg = heading + "\n" + count_msg + "\n"
                
            return device_list_msg
        except:
            print("Failed to import device list from: " + ip +"\n")
            return ""

    script_runtime_msg = ("Script Runtime: " 
        + datetime.now().strftime("%H:%M:%S - %d/%m/%Y"))
    separator_msg = ("\n" + "-"*70 + "\n")
    headerSpacing = "\n"
    body_msg = ""
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    if len(sw_host) == 1:
        try:
            print("Trying to connect to and import from: " + sw_host[0])
            swis = orionsdk.SwisClient(sw_host[0], sw_username, sw_password, verify="")
            runNewDevicesListResult = runNewDevicesList(sw_host[0])
            body_msg = runNewDevicesListResult
            if body_msg != "":
                imported = True
        except:
            print("Unable to connect to and import from: " + sw_host[0])
    elif imported == False:
        for ip in sw_host:
            try:
                if imported == False:
                    print("Trying to connect to and import from: " + ip)
                    swis = orionsdk.SwisClient(ip, sw_username, sw_password, verify="")
                    runNewDevicesListResult = runNewDevicesList(ip)
                    body_msg = runNewDevicesListResult
                    if body_msg != "":
                        imported = True
            except:
                print("Unable to connect to and import from: " + ip)
            
    #runNewDevicesListResult = runNewDevicesList()
    #body_msg = runNewDevicesListResult
    
    if enable_email_notification == "True":
        #print("Testing availability of SMTP server: " + email_server)
        if imported == False:
            email_test_result = test_email_server(email_server)
            if email_test_result:
                if body_msg != "":
                    if email_on_import == "True":
                        body_msg = script_runtime_msg + "\n\n\n" + body_msg
                        sendmail(body_msg)
                        print("\nMessage Sent:\n" + separator_msg + body_msg 
                            + separator_msg)
                else:
                    if email_on_failure == "True":
                        body_msg = (script_runtime_msg 
                            + "\n\n\nntw-menu device list could not be imported!")
                        sendmail(body_msg)
                        print("Message Sent:\n" + separator_msg + body_msg 
                            + separator_msg)
            else:
                print("unable to send e-mail notifications")

if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except IndexError:
        print("You need to enter at least 1 parameters for the script to run."
            + "\n1. RegExp search to restrict the number of devices matched and "
            + "action performed ( .* to match all )")
