#!/bin/bash

#close any existing network
./network/network.sh down

#start the network
./network/network.sh up -s couchdb

#create the channel
./network/network.sh createChannel -c localchannel 
./network/network.sh createChannel -c globalchannel


#deploy the chaincode
./network/network.sh deployCC -c localchannel -ccn mycc -ccp ../../chaincode -ccl go
./network/network.sh deployCC -c globalchannel -ccn mycc -ccp ../../chaincode -ccl go


# set the environment variables for the peer for CLI usage
export PATH=${PWD}/bin:$PATH
export FABRIC_CFG_PATH=$PWD/config/
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID="Org1MSP"
export CORE_PEER_TLS_ROOTCERT_FILE=${PWD}/network/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export CORE_PEER_MSPCONFIGPATH=${PWD}/network/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_ADDRESS=localhost:7051

# CouchDB credentials and URL
COUCHDB_URL="http://localhost:5984"
COUCHDB_USERNAME="admin"
COUCHDB_PASSWORD="adminpw"
NEW_DB_NAMES=("local_model_updates" "global_model_updates")

# Function to create a database
create_database() {
    local db_name=$1
    curl -X PUT "$COUCHDB_URL/$db_name" \
         --user $COUCHDB_USERNAME:$COUCHDB_PASSWORD

    # Check if the database was created successfully
    if [ $? -eq 0 ]; then
        echo "Database '$db_name' created successfully."
    else
        echo "Failed to create database '$db_name'."
    fi
}

# Loop through the database names and create them
for db_name in "${NEW_DB_NAMES[@]}"; do
    create_database $db_name
done

# initialize the ledger
peer chaincode invoke -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile "${PWD}/network/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem" -C localchannel -n mycc --peerAddresses localhost:7051 --tlsRootCertFiles "${PWD}/network/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt" --peerAddresses localhost:9051 --tlsRootCertFiles "${PWD}/network/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt" -c '{"function":"InitLedger","Args":[]}'

peer chaincode invoke -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile "${PWD}/network/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem" -C globalchannel -n mycc --peerAddresses localhost:7051 --tlsRootCertFiles "${PWD}/network/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt" --peerAddresses localhost:9051 --tlsRootCertFiles "${PWD}/network/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt" -c '{"function":"InitLedger","Args":[]}'

# generate the key context for Homomorphic Encryption
# number of clients = 3
export NUM_CLIENTS=3
../gen_HE_context.py $NUM_CLIENTS