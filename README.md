# Hyperledger Fabric Implementation for Capstone

## Dependencies:

* Python >3.8
* Python Torch, scikit-learn, pandas, numpy, requests, fuzzywuzzy, python-Levenshtein, tenseal, ezkl, onnx modules-

    can be installed by runnning:

    ```pip install -r requirements.txt```
* Docker (Any latest version)
* go (Any latest version)

## Setup steps:
1) make the following file executable:
    ```
    $ chmod +x ./gen_HE_context.py
    ```

2) create a file called ".env"
    ```
    COUCHDB_USERNAME = yourcouchdbusername
    COUCHDB_PASSWORD = yourcouchdbpassword
    ```

3) Place the above .env file in the directory:
    
    communicator

## Steps to Run Project (to be done in order)
1) First open 1 terminal window:
    ```
    $ cd fabric
    $ source ./initializefabric.sh
    ```

2) Now open 2nd terminal window:
    ```
    $ cd communicator
    $ go run main.go
    ```

3) Now Open a 3rd terminal window:
    ```
    $ cd verifier
    $ python3 main.py
    ```

4) Now open a 4th terminal window with 3 separate tabs:

    on each terminal: 
    ```
    # cd into each client folder in each tab
    $ cd clients/clientx # x = 1, 2, 3
    $ python3 trainer.py
    ```
5) Open another terminal in aggegator folder:
    ```
    $ cd aggregator
    $ python3 main.py
    ```
6) Go back to the 3 client terminals and enter:
    ```
    $ cd clients/clientx # x = 1, 2, 3
    $ python3 main.py
    ```

after initializing the fabric, 
* one can view the CouchDB interface on ```http://localhost/5984/_utils```
* one can view the ledger by using **peer query** commands on the CLI
