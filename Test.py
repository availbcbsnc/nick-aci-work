#!/usr/bin/env python

'''
below is the default info logging into the fabrics. line 7-21
'''

import snapshot
import get_token
import logging
from logging.handlers import RotatingFileHandler
import json
import requests
import sys
import re
import time

def login():

    #Logs into fabric and saves token, url and change number
    login = get_token.get_token()
    token = login[0]
    fabric = login[1]
    change = login[2]
    return(token)

def main(): 
    while True: 
        TN = input("\nDo you want to login? ")
        if TN != "y" and TN != "n":
            print("Please enter y or n.")
            continue
        elif TN == "y":
           A=login()
           print(A)
           break
        else:
            print("Cannot login")
            continue

if __name__ == '__main__':
    main()