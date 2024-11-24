package web

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"log"
	"github.com/hyperledger/fabric-gateway/pkg/client"
)

// Invoke handles chaincode invoke requests.
func (setup *OrgSetup) Invoke(w http.ResponseWriter, r *http.Request) {
	log.Printf("--Invoke Request Initiated--")

	// Parse JSON body
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Unable to read request body", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	// Unmarshal JSON data to extract participant_id
	var modelUpdate map[string]interface{}
	if err := json.Unmarshal(body, &modelUpdate); err != nil {
		http.Error(w, "Failed to unmarshal JSON data", http.StatusBadRequest)
		return
	}

	participantID, ok := modelUpdate["participant_id"].(string)
	if !ok {
		http.Error(w, "Missing or invalid participant_id in JSON data", http.StatusBadRequest)
		return
	}

	// Extract query parameters
	queryParams := r.URL.Query()

	chainCodeName := queryParams.Get("chaincodeid")
	locality := queryParams.Get("locality")
	channelID := locality + "channel"
	function := queryParams.Get("function")
	args := r.Form["args"]

	dbName := locality + "_model_updates"

	// Prepare form-encoded data
	data := url.Values{}
	data.Set("db", dbName)

	dbURL := "http://localhost:50051/db"
	req, err := http.NewRequest("POST", dbURL, bytes.NewReader(body))
	if err != nil {
		http.Error(w, "Failed to create request", http.StatusInternalServerError)
		return
	}

	req.Header.Set("Content-Type", "application/json")
	req.URL.RawQuery = data.Encode()

	httpClient := &http.Client{}
	resp, err := httpClient.Do(req)
	if err != nil {
		http.Error(w, "Failed to send request to /db", http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	// Read response from /db
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		http.Error(w, "Failed to read response from /db", http.StatusInternalServerError)
		return
	}

	if resp.StatusCode != http.StatusCreated {
		http.Error(w, string(respBody), resp.StatusCode)
		return
	}

	var dbResponse map[string]interface{}
	if err := json.Unmarshal(respBody, &dbResponse); err != nil {
		http.Error(w, "Failed to unmarshal response from /db", http.StatusInternalServerError)
		return
	}

	docID, ok := dbResponse["id"].(string)
	if !ok {
		http.Error(w, "Failed to retrieve document ID from /db response", http.StatusInternalServerError)
		return
	}

	args = append(args, participantID, docID)

	log.Printf("Invoking Ledger : channel: %s, chaincode: %s, function: %s, args: %s\n", channelID, chainCodeName, function, args)
	network := setup.Gateway.GetNetwork(channelID)
	contract := network.GetContract(chainCodeName)
	txn_proposal, err := contract.NewProposal(function, client.WithArguments(args...))
	if err != nil {
		fmt.Fprintf(w, "Error creating txn proposal: %s", err)
		return
	}
	txn_endorsed, err := txn_proposal.Endorse()
	if err != nil {
		fmt.Fprintf(w, "Error endorsing txn: %s", err)
		return
	}
	txn_committed, err := txn_endorsed.Submit()
	if err != nil {
		fmt.Fprintf(w, "Error submitting transaction: %s", err)
		return
	}
	fmt.Fprintf(w, "SUCCESS : Model Update Submitted (Transaction ID:  %s)\n", txn_committed.TransactionID())
	log.Printf("--Invoke Request Completed--")
}
