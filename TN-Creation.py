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

#Logs into fabric and saves token, url and change number
login = get_token.get_token()
token = login[0]
fabric = login[1]
change = login[2]

while True:
    TN = input("\nEnter your TN Name: ")
    ans = input("You entered " + str(TN) + " is this correct? (y or n): ")
    ans_low = ans.lower()
    if ans_low != "y" and ans_low != "n":
        print("Please enter y or n.")
        continue
    elif ans_low == "y":
        details["TN"] = TN
        break
    else:
        continue
print(TN)