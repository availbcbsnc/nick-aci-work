#!/usr/bin/env python

'''
   This script will get all policy groups and format them into a list


    File name: port_config.py
    Version: 1.2
    Author: Nicholas Bogdajewicz
    Date created: 4/12/2022
    Date last modified: 4/12/2022
    Python Version: 3.8.2
    requests version: 2.27.0
'''

import snapshot
import get_token
import json
import requests

#Logs into fabric and saves token, url and change number
login = get_token.get_token()
token = login[0]
fabric = login[1]
change = login[2]


def main():

    policy_group = []

    #gets access policy_groups
    url = fabric + "/api/node/class/infraAccPortGrp.json"          
    headers = {
        "Cookie" : f"APIC-Cookie={token}", 
    }
    requests.packages.urllib3.disable_warnings()
    response = requests.get(url, headers=headers, verify=False)
    response_json = json.loads(response.text)

    child_obj = response_json["imdata"]

    for item in child_obj:
        group = item["infraAccPortGrp"]["attributes"]["name"]

        policy_group.append({'lag_type': 'leaf', 'policy_group': group})   
        
    #gets po and vpc policy_groups
    url = fabric + "/api/node/class/infraAccBndlGrp.json"          
    headers = {
        "Cookie" : f"APIC-Cookie={token}", 
    }
    requests.packages.urllib3.disable_warnings()
    response = requests.get(url, headers=headers, verify=False)
    response_json = json.loads(response.text)

    child_obj = response_json["imdata"]

    for item in child_obj:
        group = item["infraAccBndlGrp"]["attributes"]["name"]
        type = item["infraAccBndlGrp"]["attributes"]["lagT"]

        policy_group.append({'lag_type': type, 'policy_group': group})   


    #print(policy_group)

    #apply storm control to all access policy groups
    for item in policy_group:
        
        if item["lag_type"] == "leaf":
            class_type = "accportgrp"
        else:
            class_type = "accbundle"

        storm_policy = "SVS_Recommended"

        url = fabric + "/api/node/mo/uni/infra/funcprof/" + class_type + "-" + item["policy_group"] + "/rsstormctrlIfPol.json"          
        headers = {
            "Cookie" : f"APIC-Cookie={token}", 
        }

        payload = {"infraRsStormctrlIfPol":{"attributes":{"tnStormctrlIfPolName":storm_policy},"children":[]}}
        data = json.dumps(payload)

        requests.packages.urllib3.disable_warnings()
        response = requests.post(url, data=data, headers=headers, verify=False)
        response_json = json.loads(response.text)

        if response.status_code != 200:
            print("ERROR! Could not deploy policy on " + item["policy_group"] + " " + str(response))
        else:
            print(storm_policy + " deployed on policy group: " + item["policy_group"])


if __name__ == '__main__':
    main()