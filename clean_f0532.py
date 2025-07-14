#!/usr/bin/env python

'''
   The purpose of this script is to gather all of the EPGs for each interface that has been down for 30 days using fault F0532. It will then create a URL and Payload for each static port, which you can then use to remove the old config.


    File name: clean-f0532.py
    Author: Nicholas Bogdajewicz
    Date created: 3/05/2022
    Date last modified: 3/05/2022
    Python Version: 3.8.2
    requests version: 2.27.0
'''

import get_token
import snapshot

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


'''
This function will grab all F0532 faults that are greater than X days
'''
def get_f0532():
    global token, timer

    #Creates variable for X number of days before current date
    start_date = datetime.date.today() - datetime.timedelta(30)

    c_timer = time.time()
    d_timer = c_timer - timer
    if d_timer >= 540:
        token = get_token.refresh_token(fabric, token)
        timer = time.time()

    #Sends API request for F0532 faults before start_date and saves as response_json
    url = fabric + f"/api/node/class/faultInst.json?query-target-filter=and(and(eq(faultInfo.code,\"F0532\")),lt(faultInfo.lastTransition, \"{start_date}\"))"

    headers = {
        "Cookie" : f"APIC-Cookie={token}", 
    }

    requests.packages.urllib3.disable_warnings()
    response = requests.get(url, headers=headers, verify=False)

    #If not status code 200, skip request
    if response.status_code != 200:
        print("ERROR! Could not get the list of F0532 faults. response: " + str(response))
        sys.exit()

    response_json = json.loads(response.text)

    #Formats date and counts number of faults then prints it
    olddate = start_date.strftime("%Y-%m-%d")
    fault_count = str(len(response_json["imdata"]))
    print("\n" + fault_count + " F0532 faults are older than: " + olddate + "\n")

    #logs and returns faults
    return(response_json)


'''
This function determines if the interface is a standalone interface, port-channel or vpc.
'''
def split_int(item):
    global token, timer

    #grabs node id and interface
    node_intf = item["faultInst"]["attributes"]["dn"]
    reg = re.findall(r'\w+', node_intf)
    nodes = reg[4]
    intfs = reg[7]
    eths = "/" + reg[8]


    #splits eth and po interfaces into seperate lists
    if re.search('eth.+', intfs):
        eth_int = {"node": nodes, "interface": intfs + eths}
    else:
        po_int = {"node": nodes, "interface": intfs}
        eth_int = {}

    #Checks if ethernet interface is in a port-channel or not
    if eth_int != {}:
        node = str(eth_int["node"])
        intf = (eth_int["interface"])

        c_timer = time.time()
        d_timer = c_timer - timer
        if d_timer >= 540:
            token = get_token.refresh_token(fabric, token)
            timer = time.time()

        url = fabric + "/api/node/mo/topology/pod-1/node-" + node + "/sys/phys-[" + intf + "].json?query-target=children&target-subtree-class=relnFrom"
        headers = {
            "Cookie" : f"APIC-Cookie={token}", 
        }
        requests.packages.urllib3.disable_warnings()
        response = requests.get(url, headers=headers, verify=False)

        #If not status code 200, skip request
        if response.status_code != 200:
            print("ERROR! Could not determine if node " + node + " interface " + intf + " is in a port-channel or not.")
            return

        response_json = json.loads(response.text)

        child_obj = response_json["imdata"]

        if any("l1RtMbrIfs" in d for d in child_obj):
            #if so grab the po id and move to vpc check
            sort = sorted(child_obj, key=lambda d: list(d.keys()), reverse=True)
            po_id = sort[2]["l1RtMbrIfs"]["attributes"]["tSKey"]
            po_int = {"node": eth_int["node"], "interface": po_id}
            #checks if fault exists on po, if so skip to avoid duplicates
            c_timer = time.time()
            d_timer = c_timer - timer
            if d_timer >= 540:
                token = get_token.refresh_token(fabric, token)
                timer = time.time()

            url = fabric + "/api/node/mo/topology/pod-1/node-" + po_int["node"] + "/sys/aggr-[" + po_int["interface"] + "].json?rsp-subtree-include=faults,no-scoped,subtree&query-target-filter=eq(faultInst.code, \"F0532\")"
            headers = {
                "Cookie" : f"APIC-Cookie={token}", 
            }
            requests.packages.urllib3.disable_warnings()
            response = requests.get(url, headers=headers, verify=False)

            #If not status code 200, skip request
            if response.status_code != 200:
                print("ERROR! Could not determine if node " + po_int["node"] + " interface " + po_int["po_id"] + " has fault F0532.")
                return

            response_json = json.loads(response.text)

            if response_json["imdata"] != []:
                return

        else:
            #if not return to main for loop
            eth_int = {"type": "standalone", "node": eth_int["node"], "interface": eth_int["interface"]}
            return eth_int


    #determines in po interface is part of a vpc or not
    c_timer = time.time()
    d_timer = c_timer - timer
    if d_timer >= 540:
        token = get_token.refresh_token(fabric, token)
        timer = time.time()

    url = fabric + "/api/node/mo/topology/pod-1/node-" + po_int["node"] + "/sys/aggr-[" + po_int["interface"] + "].json?query-target=children&target-subtree-class=relnFrom"
    headers = {
        "Cookie" : f"APIC-Cookie={token}", 
    }
    requests.packages.urllib3.disable_warnings()
    response = requests.get(url, headers=headers, verify=False)

    #If not status code 200, skip request
    if response.status_code != 200:
        print("ERROR! Could not determine if node " + po_int["node"] + " interface " + po_int["interface"] + " is in a VPC or not.")
        return

    response_json = json.loads(response.text)

    child_obj = response_json["imdata"]

    #checks if vpc attribute exists and splits po and vpc int. as well as grabbing policy group info and vpc ids
    if any("pcRtVpcConf" in d for d in child_obj):
        if int(po_int["node"]) % 2 != 0:
            sort = sorted(child_obj, key=lambda d: list(d.keys()), reverse=True)
            vpc_id = sort[0]["pcRtVpcConf"]["attributes"]["tSKey"]
            dom_id = sort[0]["pcRtVpcConf"]["attributes"]["tDn"]
            reg = re.findall(r'\w+', dom_id)
            policy_group = sort[1]["pcRtAccBndlGrpToAggrIf"]["attributes"]["tDn"]
            reg2 = re.findall('(?<=accbundle-).*$', policy_group)[0]
            vpc_int = {"type": "VPC", "node": po_int["node"], "interface": po_int["interface"], "vpc_id": vpc_id, "dom_id": reg[9], "policy_group": reg2}
            return vpc_int
        else: 
            return
    else:
        sort = sorted(child_obj, key=lambda d: list(d.keys()), reverse=True)
        policy_group = sort[0]["pcRtAccBndlGrpToAggrIf"]["attributes"]["tDn"]
        reg = re.findall('(?<=accbundle-).*$', policy_group)[0]
        po_int = {"type": "port-channel", "node": po_int["node"], "interface": po_int["interface"], "policy_group": reg}
        return po_int


'''
This function verify if the physical interface is up for both phy and po interfaces
'''
def int_status(item):
    global token, timer

    #checks standalone interfaces to confirm they are not up
    if item["type"] == "standalone":
        node = str(item["node"])
        intf = item["interface"]

        c_timer = time.time()
        d_timer = c_timer - timer
        if d_timer >= 540:
            token = get_token.refresh_token(fabric, token)
            timer = time.time()

        url = fabric + "/api/node/mo/topology/pod-1/node-" + node + "/sys/phys-[" + intf + "].json?query-target=children&target-subtree-class=ethpmPhysIf"
        headers = {
            "Cookie" : f"APIC-Cookie={token}", 
        }
        requests.packages.urllib3.disable_warnings()
        response = requests.get(url, headers=headers, verify=False)

        #If not status code 200, skip request
        if response.status_code != 200:
            print("ERROR! Could not determine if node " + node + " interface " + intf + " is down or not.")
            return

        response_json = json.loads(response.text)

        #grabs the status and operation state. ignores if up or admin shut.
        child_obj = response_json["imdata"][0]["ethpmPhysIf"]["attributes"]["operSt"]
        blck = response_json["imdata"][0]["ethpmPhysIf"]["attributes"]["usage"]

        if blck == "blacklist" or blck == "blacklist,epg":
            print("Skipping interface as it's admin disabled.")
            return
        elif child_obj == "up":
            print("Skipping interface as its operational state is up.")
            return
        elif child_obj == "down" and blck == "epg":
            print("Interface is down and not admin disabled.")
            return item
        else:
            print("Skipping interface as its state is unknown.")
            return

    #checks po interfaces to confirm they are not up. Gets physical interfaces in the port channel
    if item["type"] == "port-channel" or item["type"] == "VPC":    
        node = str(item["node"])
        intf = (item["interface"])

        c_timer = time.time()
        d_timer = c_timer - timer
        if d_timer >= 540:
            token = get_token.refresh_token(fabric, token)
            timer = time.time()

        url = fabric + "/api/node/mo/topology/pod-1/node-" + node + "/sys/aggr-[" + intf + "].json?query-target=children&target-subtree-class=pcRsMbrIfs"
        headers = {
            "Cookie" : f"APIC-Cookie={token}", 
        }
        requests.packages.urllib3.disable_warnings()
        response = requests.get(url, headers=headers, verify=False)

        #If not status code 200, skip request
        if response.status_code != 200:
            print("ERROR! Could not determine if node " + node + " interface " + intf + " is down or not.")
            return

        response_json = json.loads(response.text)
        
        child_obj = response_json["imdata"]

        phy_int = []
        #loops through phy interfaces and saves in list
        for phy in child_obj:
            phy_int.append(phy["pcRsMbrIfs"]["attributes"]["tSKey"])

        #loops through the list and checks the interface status
        status = []
        usage = []
        for stat in phy_int:
            c_timer = time.time()
            d_timer = c_timer - timer
            if d_timer >= 540:
                token = get_token.refresh_token(fabric, token)
                timer = time.time()
                
            url = fabric + "/api/node/mo/topology/pod-1/node-" + node + "/sys/phys-[" + stat + "].json?query-target=children&target-subtree-class=ethpmPhysIf"
            headers = {
            "Cookie" : f"APIC-Cookie={token}", 
            }
            requests.packages.urllib3.disable_warnings()
            response = requests.get(url, headers=headers, verify=False)

            #If not status code 200, skip request
            if response.status_code != 200:
                print("ERROR! Could not determine if node " + node + " interface " + stat + " is down or not.")
                return

            response_json = json.loads(response.text)
            op_stat = response_json["imdata"][0]["ethpmPhysIf"]["attributes"]["operSt"]
            blck = response_json["imdata"][0]["ethpmPhysIf"]["attributes"]["usage"]
            reg = re.findall(r'\w+', blck)
            status.append(op_stat)
            usage.append(reg[0])

        #if any up interfaces in list ignore
        if item["type"] == "port-channel":
            if "blacklist" in usage or "blacklist,epg" in usage:
                print("Skipping, interface in port-channel is admin disabled.")
                return
            elif "up" in status:
                print("Skipping, interface in port-channel operational state is up.")
                return
            elif "down" in status and "epg" in usage:
                print("Interfaces in port-channel are down and not admin disabled.")
                return item
            else:
                print("Skipping, interface in port-channel state is unknown.")
                return

        #if any up interfaces in list ignore
        if item["type"] == "VPC":
            if "blacklist" in usage or "blacklist,epg" in usage:
                print("Skipping, interface in port-channel is admin disabled.")
                return
            elif "up" in status:
                print("Skipping, interface in port-channel operational state is up.")
                return
            elif "down" in status and "epg" in usage:
                print("Interfaces in port-channel are down and not admin disabled.")

                #checks vpc peer interfaces
                dom = item["dom_id"]
                vpc = item["vpc_id"]

                c_timer = time.time()
                d_timer = c_timer - timer
                if d_timer >= 540:
                    token = get_token.refresh_token(fabric, token)
                    timer = time.time()

                url = fabric + "/api/node/mo/topology/pod-1/node-" + str(int(node) + 1) + "/sys/vpc/inst/dom-" + dom + "/if-" + vpc + ".json?query-target=children&target-subtree-class=vpcRsVpcConf"
                headers = {
                    "Cookie" : f"APIC-Cookie={token}", 
                }
                requests.packages.urllib3.disable_warnings()
                response = requests.get(url, headers=headers, verify=False)
                #If not status code 200, skip request
                if response.status_code != 200:
                    print("ERROR! Could not determine if node " + node + " VPC peers interfaces are down or not.")
                    return

                response_json = json.loads(response.text)
                po = response_json["imdata"][0]["vpcRsVpcConf"]["attributes"]["tSKey"]

                c_timer = time.time()
                d_timer = c_timer - timer
                if d_timer >= 540:
                    token = get_token.refresh_token(fabric, token)
                    timer = time.time()

                url = fabric + "/api/node/mo/topology/pod-1/node-" + str(int(node) + 1) + "/sys/aggr-[" + po + "].json?query-target=children&target-subtree-class=pcRsMbrIfs"
                headers = {
                    "Cookie" : f"APIC-Cookie={token}", 
                }
                requests.packages.urllib3.disable_warnings()
                response = requests.get(url, headers=headers, verify=False)
                #If not status code 200, skip request
                if response.status_code != 200:
                    print("ERROR! Could not determine if node " + node + " VPC peers interfaces are down or not.")
                    return

                response_json = json.loads(response.text)
                child_obj = response_json["imdata"]

                phy_int = []
                #loops through phy interfaces and saves in list
                for phy in child_obj:
                    phy_int.append(phy["pcRsMbrIfs"]["attributes"]["tSKey"])

                #loops through the list and checks the interface status
                status = []
                usage = []
                for stat in phy_int:

                    c_timer = time.time()
                    d_timer = c_timer - timer
                    if d_timer >= 540:
                        token = get_token.refresh_token(fabric, token)
                        timer = time.time()

                    url = fabric + "/api/node/mo/topology/pod-1/node-" + str(int(node) + 1) + "/sys/phys-[" + stat + "].json?query-target=children&target-subtree-class=ethpmPhysIf"
                    headers = {
                        "Cookie" : f"APIC-Cookie={token}", 
                    }
                    requests.packages.urllib3.disable_warnings()
                    response = requests.get(url, headers=headers, verify=False)

                    response_json = json.loads(response.text)
                    op_stat = response_json["imdata"][0]["ethpmPhysIf"]["attributes"]["operSt"]
                    blck = response_json["imdata"][0]["ethpmPhysIf"]["attributes"]["usage"]
                    reg = re.findall(r'\w+', blck)
                    status.append(op_stat)
                    usage.append(reg[0])
                #if any up interfaces in list ignore.
                if "blacklist" in usage or "blacklist,epg" in usage:
                    print("Skipping, interface in VPC peers port-channel is admin disabled.")
                    return
                elif "up" in status:
                    print("Skipping, interface in VPC peers port-channel operational state is up.")
                    return
                elif "down" in status and "epg" in usage:
                    print("Interfaces in VPC peers port-channel are down and not admin disabled.")
                    return item
                else:
                    print("Skipping, interface in VPC peers port-channel state is unknown.")
                    return

            else:
                print("Skipping, interface in port-channel state is unknown.")
                return


'''
This function will grab all epgs for down interfaces
'''
def get_epg(item):
    global token, timer

    if item["type"] == "standalone":
        node = str(item["node"])
        intf = item["interface"]

        c_timer = time.time()
        d_timer = c_timer - timer
        if d_timer >= 540:
            token = get_token.refresh_token(fabric, token)
            timer = time.time()

        url = fabric + "/api/node/mo/topology/pod-1/node-" + node + "/sys/phys-[" + intf + "].json?rsp-subtree-include=full-deployment&target-node=all&target-path=l1EthIfToEPg"
        headers = {
            "Cookie" : f"APIC-Cookie={token}", 
        }
        requests.packages.urllib3.disable_warnings()
        response = requests.get(url, headers=headers, verify=False)
        #If not status code 200, skip request
        if response.status_code != 200:
            print("ERROR! Could not determine EPGs on node " + node + " interface " + intf)
            return

        response_json = json.loads(response.text)

        obj = response_json["imdata"][0]["l1PhysIf"]

        #checks if any epgs exist
        if any("children" in d for d in obj):
            child_obj = response_json["imdata"][0]["l1PhysIf"]["children"][0]["pconsCtrlrDeployCtx"]["children"]
        else:
            print("No EPGs detected on node " + node + " interface " + intf)
            return

        #appends list of epgs to dictionary
        list1 = []
        for dic in child_obj:
            for val in dic.values():
                if not isinstance(val, dict):
                    print(val)
            else:
                for val2 in val.values():
                    list1.append(val2["ctxDn"])
        
        item["epg"] = list1
        return item


    if item["type"] == "port-channel" or item["type"] == "VPC":
        node = str(item["node"])
        intf = item["interface"]

        c_timer = time.time()
        d_timer = c_timer - timer
        if d_timer >= 540:
            token = get_token.refresh_token(fabric, token)
            timer = time.time()

        url = fabric + "/api/node/mo/topology/pod-1/node-" + node + "/sys/aggr-" + intf + ".json?rsp-subtree-include=full-deployment&target-node=all&target-path=l1EthIfToEPg"
        headers = {
            "Cookie" : f"APIC-Cookie={token}", 
        }
        requests.packages.urllib3.disable_warnings()
        response = requests.get(url, headers=headers, verify=False)
        #If not status code 200, skip request
        if response.status_code != 200:
            print("ERROR! Could not determine EPGs on node " + node + " interface " + intf)
            return

        response_json = json.loads(response.text)

        obj = response_json["imdata"][0]["pcAggrIf"]

        if any("children" in d for d in obj):
            child_obj = response_json["imdata"][0]["pcAggrIf"]["children"][0]["pconsCtrlrDeployCtx"]["children"]
        else: 
            print("No EPGs detected on node " + node + " interface " + intf)
            return

        list1 = []
        for dic in child_obj:
            for val in dic.values():
                if not isinstance(val, dict):
                    print(val)
            else:
                for val2 in val.values():
                    list1.append(val2["ctxDn"])

        item["epg"] = list1
        return item


'''
This function will remove any down interfaces from the EPGs
'''
def remove_port(epg):
    global token, timer

    #loops through epgs
    for item in epg["epg"]:

        #formats for vpc or access
        if epg["type"] == "standalone":
            node = epg["node"]
            paths = "paths-"
            interface = epg["interface"]
        elif epg["type"] == "port-channel":
            node = epg["node"]
            paths = "paths-"
            interface = epg["policy_group"]
        elif epg["type"] == "VPC":
            node = epg["node"] + "-" + str(int(epg["node"]) + 1)
            paths = "protpaths-"
            interface = epg["policy_group"]

        c_timer = time.time()
        d_timer = c_timer - timer
        if d_timer >= 540:
            token = get_token.refresh_token(fabric, token)
            timer = time.time()

        url = fabric + "/api/node/mo/" + item + "/rspathAtt-[topology/pod-1/" + paths + node + "/pathep-[" + interface + "]].json"

        headers = {
            "Cookie" : f"APIC-Cookie={token}", 
        }

        payload = {"fvRsPathAtt":{"attributes":{"dn": item + "/rspathAtt-[topology/pod-1/"  + paths + node + "/pathep-[" + interface + "]]","status":"deleted"},"children":[]}}

        data = json.dumps(payload)
        requests.packages.urllib3.disable_warnings()
        response = requests.post(url, data=data, headers=headers, verify=False)

        #If not status code 200, skip request
        if response.status_code != 200:
            print("ERROR! Could not remove port " + epg["policy_group"] + " on node " + node + " from epg " + item)
            continue

        response_json = json.loads(response.text)

        if response.status_code == 200:
            print("Node " + node + " Interface " + interface + " removed from " + item)


def main():
    global token, timer
    snapshot.snapshot_pre(change, token, fabric)

    #Gets all F0532 faults > 30 days
    fault = get_f0532()

    counter = 0
    #Loops through faults
    for item in fault["imdata"]:

        #calls function to split into physical, port channel or vpc group
        interface = split_int(item)

        if interface == None:
            continue
        elif interface["type"] == "standalone":
            counter += 1
            print("-----Request: " + str(counter) + "-----")
            print("Processing fault F0532: " + item["faultInst"]["attributes"]["dn"])
            print("Standalone interface " + interface["interface"] + " on node " + interface["node"])
        elif interface["type"] == "port-channel":
            counter += 1
            print("-----Request: " + str(counter) + "-----")
            print("Processing fault F0532: " + item["faultInst"]["attributes"]["dn"])
            print("Port-channel interface " + interface["policy_group"] + " on node " + interface["node"])
        elif interface["type"] == "VPC":
            counter += 1
            print("-----Request: " + str(counter) + "-----")
            print("Processing fault F0532: " + item["faultInst"]["attributes"]["dn"])
            print("VPC interface " + interface["policy_group"] + " on node " + interface["node"] + "-" + str(int(interface["node"]) + 1))

        status = int_status(interface)

        if status == None:
            print("")
            continue

        epg = get_epg(status)

        if epg == None:
            print("")
            continue
        else:
            print("Number of EPGs on interface : " + str(len(epg["epg"])))
            delete_stat = remove_port(epg)
            if delete_stat == None:
                print("")
                continue
        print("")
        time.sleep(2)


    snapshot.snapshot_post(change, token, fabric)

if __name__ == '__main__':
    main()