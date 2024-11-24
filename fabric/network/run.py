# Script to run the entire process of creating network and working with chaincode

import os
import subprocess

subprocess.run(["./network.sh", "up"])
subprocess.run(["./network.sh", "createChannel"])

print("***************************************************************")
print("Network has been created and a channel named 'mychannel' has been created")
print()

response = input("Do you want to: (1)deploy chaincode (2) exit? [1/(2)]")

if response == "2":
    subprocess.run(["./network.sh", "down"], check=True)
    exit()

print("***************************************************************")
print("You chose to deploy chaincode")
print()

# ./network.sh deployCC -ccn {name_you_want_to_give} -ccp {path_to_chaincode} -ccl {language}
subprocess.run(["./network.sh", "deployCC", "-ccn", "basic", "-ccp", "../asset-transfer-basic/chaincode-go", "-ccl", "go"])

env = os.environ.copy()
env["PATH"] = f"{os.getcwd()}/../bin:" + env["PATH"]
env["FABRIC_CFG_PATH"] = os.getcwd() + "/../config/"

while True:
    