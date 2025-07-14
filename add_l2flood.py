#!/usr/bin/env python

'''
   This script will find legacy l2 BDs and change l2 unknown unicast to flood.


    File name: add_l2flood.py
    Author: Nicholas Bogdajewicz
    Date created: 2/14/2023
    Date last modified: 2/14/2023
    Python Version: 3.8.2
    requests version: 2.27.0
'''

import get_token
import snapshot
import logging
from logging.handlers import RotatingFileHandler
import sys
import time
import requests
import json
import datetime
import re


#Logs into fabric and saves token, url and change number
login = get_token.get_token()
token = login[0]
fabric = login[1]
change = login[2]
timer = time.time()


def get_bds():
    global token, timer
    
    c_timer = time.time()
    d_timer = c_timer - timer
    if d_timer >= 540:
        token = get_token.refresh_token(fabric, token)
        timer = time.time()
    if d_timer >= 600:
        token = get_token.get_token()
        timer = time.time()

    url = fabric + "/api/class/fvBD.json"

    headers = {
        "Cookie" : f"APIC-Cookie={token}", 
    }

    requests.packages.urllib3.disable_warnings()
    response = requests.get(url, headers=headers, verify=False)

    #If not status code 200, skip request
    if response.status_code != 200:
        print("Error! Could not retreive list of bridge domains.")
        print(response)
        sys.exit()

    response_json = json.loads(response.text)

    return(response_json["imdata"])


def main():
    global token, timer
    snapshot.snapshot_pre(change, token, fabric)

    bdlist = get_bds()

    for item in bdlist:

        bd_dn = item["fvBD"]["attributes"]["dn"]

        c_timer = time.time()
        d_timer = c_timer - timer
        if d_timer >= 540:
            token = get_token.refresh_token(fabric, token)
            timer = time.time()
        if d_timer >= 600:
            token = get_token.get_token()
            timer = time.time()

        url = fabric + "/api/mo/" + bd_dn + ".json?rsp-subtree=full&rsp-subtree-class=fvSubnet"

        headers = {
            "Cookie" : f"APIC-Cookie={token}", 
        }

        requests.packages.urllib3.disable_warnings()
        response = requests.get(url, headers=headers, verify=False)

        #If not status code 200, skip request
        if response.status_code != 200:
            print("Error! Could not retreive subnets from bridge domain.")
            print(response)
            continue

        response_json = json.loads(response.text)

        if "children" in response_json["imdata"][0]["fvBD"]:
            if response_json["imdata"][0]["fvBD"]["attributes"]["unicastRoute"] == "yes":
                continue
            else:
                for item in response_json["imdata"][0]["fvBD"]["children"]:
                    subnet = item["fvSubnet"]["attributes"]["ip"]

                    c_timer = time.time()
                    d_timer = c_timer - timer
                    if d_timer >= 540:
                        token = get_token.refresh_token(fabric, token)
                        timer = time.time()
                    if d_timer >= 600:
                        token = get_token.get_token()
                        timer = time.time()

                    url = fabric + "/api/node/mo/" + bd_dn + "/subnet-[" + subnet + "].json"

                    headers = {
                        "Cookie" : f"APIC-Cookie={token}", 
                    }

                    payload = {"fvSubnet":{"attributes":{"dn":bd_dn + "/subnet-[" + subnet + "]","status":"deleted"},"children":[]}}
                    data = json.dumps(payload)

                    requests.packages.urllib3.disable_warnings()
                    response = requests.post(url, data=data, headers=headers, verify=False)

                    #If not status code 200, skip request
                    if response.status_code != 200:
                        print("Error! Could not remove subnet for " + bd_dn + ".")
                        print(response)
                        continue
                    else:
                        print("Subnet " + subnet + " removed from " + bd_dn)


                if response_json["imdata"][0]["fvBD"]["attributes"]["unkMacUcastAct"] == "proxy":
                    c_timer = time.time()
                    d_timer = c_timer - timer
                    if d_timer >= 540:
                        token = get_token.refresh_token(fabric, token)
                        timer = time.time()
                    if d_timer >= 600:
                        token = get_token.get_token()
                        timer = time.time()

                    url = fabric + "/api/node/mo/" + bd_dn + ".json"

                    headers = {
                        "Cookie" : f"APIC-Cookie={token}", 
                    }

                    payload = {"fvBD":{"attributes":{"dn":bd_dn,"unkMacUcastAct":"flood","arpFlood":"true"},"children":[]}}
                    data = json.dumps(payload)

                    requests.packages.urllib3.disable_warnings()
                    response = requests.post(url, data=data, headers=headers, verify=False)

                    #If not status code 200, skip request
                    if response.status_code != 200:
                        print("Error! Could not update l2 unknown unicast for " + bd_dn + ".")
                        print(response)
                        continue
                    else:
                        print("L2 Unknown cast set to flood for " + bd_dn)

                if response_json["imdata"][0]["fvBD"]["attributes"]["arpFlood"] == "no":
            
                    c_timer = time.time()
                    d_timer = c_timer - timer
                    if d_timer >= 540:
                        token = get_token.refresh_token(fabric, token)
                        timer = time.time()
                    if d_timer >= 600:
                        token = get_token.get_token()
                        timer = time.time()

                    url = fabric + "/api/node/mo/" + bd_dn + ".json"

                    headers = {
                        "Cookie" : f"APIC-Cookie={token}", 
                    }

                    payload = {"fvBD":{"attributes":{"dn":bd_dn,"arpFlood":"true"},"children":[]}}
                    data = json.dumps(payload)

                    requests.packages.urllib3.disable_warnings()
                    response = requests.post(url, data=data, headers=headers, verify=False)

                    #If not status code 200, skip request
                    if response.status_code != 200:
                        print("Error! Could not update unicast routing for " + bd_dn + ".")
                        print(response)
                        continue
                    else:
                        print("ARP flooding enabled for " + bd_dn)  

                print("\n")
                continue

        if response_json["imdata"][0]["fvBD"]["attributes"]["unkMacUcastAct"] == "proxy":
            
            c_timer = time.time()
            d_timer = c_timer - timer
            if d_timer >= 540:
                token = get_token.refresh_token(fabric, token)
                timer = time.time()
            if d_timer >= 600:
                token = get_token.get_token()
                timer = time.time()

            url = fabric + "/api/node/mo/" + bd_dn + ".json"

            headers = {
                "Cookie" : f"APIC-Cookie={token}", 
            }

            payload = {"fvBD":{"attributes":{"dn":bd_dn,"unkMacUcastAct":"flood","arpFlood":"true"},"children":[]}}
            data = json.dumps(payload)

            requests.packages.urllib3.disable_warnings()
            response = requests.post(url, data=data, headers=headers, verify=False)

            #If not status code 200, skip request
            if response.status_code != 200:
                print("Error! Could not update l2 unknown unicast for " + bd_dn + ".")
                print(response)
                continue
            else:
                print("L2 Unknown cast set to flood for " + bd_dn)

        if response_json["imdata"][0]["fvBD"]["attributes"]["unicastRoute"] == "yes":

            c_timer = time.time()
            d_timer = c_timer - timer
            if d_timer >= 540:
                token = get_token.refresh_token(fabric, token)
                timer = time.time()
            if d_timer >= 600:
                token = get_token.get_token()
                timer = time.time()

            url = fabric + "/api/node/mo/" + bd_dn + ".json"

            headers = {
                "Cookie" : f"APIC-Cookie={token}", 
            }

            payload = {"fvBD":{"attributes":{"dn":bd_dn,"unicastRoute":"false"},"children":[]}}
            data = json.dumps(payload)

            requests.packages.urllib3.disable_warnings()
            response = requests.post(url, data=data, headers=headers, verify=False)

            #If not status code 200, skip request
            if response.status_code != 200:
                print("Error! Could not update unicast routing for " + bd_dn + ".")
                print(response)
                continue
            else:
                print("Unicast routing disabled for " + bd_dn)

        if response_json["imdata"][0]["fvBD"]["attributes"]["arpFlood"] == "no":
            c_timer = time.time()
            d_timer = c_timer - timer
            if d_timer >= 540:
                token = get_token.refresh_token(fabric, token)
                timer = time.time()
            if d_timer >= 600:
                token = get_token.get_token()
                timer = time.time()

            url = fabric + "/api/node/mo/" + bd_dn + ".json"

            headers = {
                "Cookie" : f"APIC-Cookie={token}", 
            }

            payload = {"fvBD":{"attributes":{"dn":bd_dn,"arpFlood":"true"},"children":[]}}
            data = json.dumps(payload)

            requests.packages.urllib3.disable_warnings()
            response = requests.post(url, data=data, headers=headers, verify=False)

            #If not status code 200, skip request
            if response.status_code != 200:
                print("Error! Could not update unicast routing for " + bd_dn + ".")
                print(response)
                continue
            else:
                print("ARP flooding enabled for " + bd_dn)


        if response_json["imdata"][0]["fvBD"]["attributes"]["unkMacUcastAct"] == "proxy" or response_json["imdata"][0]["fvBD"]["attributes"]["unicastRoute"] == "yes" or response_json["imdata"][0]["fvBD"]["attributes"]["arpFlood"] == "no":
            print("\n")

    snapshot.snapshot_post(change, token, fabric)

if __name__ == '__main__':
    main()