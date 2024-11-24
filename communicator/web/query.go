package web

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"log"
)

// Query handles chaincode query requests.
func (setup OrgSetup) Query(w http.ResponseWriter, r *http.Request) {
	log.Printf("--Query Request Initiated--")
	queryParams := r.URL.Query()
	chainCodeName := "mycc"
	locality := queryParams.Get("locality")
	channelID := locality + "channel"
	function := "QueryUpdate"
	args := r.URL.Query()["args"]
	log.Printf("Querying Ledger : channel: %s, chaincode: %s, function: %s, args: %s\n", channelID, chainCodeName, function, args)
	network := setup.Gateway.GetNetwork(channelID)
	contract := network.GetContract(chainCodeName)
	evaluateResponse, err := contract.EvaluateTransaction(function, args...)
	if err != nil {
		fmt.Fprintf(w, "Error: %s", err)
		return
	}

	// Parse the JSON response
	var modelUpdates []map[string]interface{}
	if err := json.Unmarshal(evaluateResponse, &modelUpdates); err != nil {
		http.Error(w, "Failed to parse JSON response", http.StatusInternalServerError)
		return
	}

	// Filter and collect DocIDs of non-default ParticipantIDs
	var docIDs []string
	for _, update := range modelUpdates {
		if participantID, ok := update["ParticipantID"].(string); ok && participantID != "default" {
			if docID, ok := update["DocID"].(string); ok {
				docIDs = append(docIDs, docID)
			}
		}
	}
	// Print all values of docIDs
	fmt.Println("DocIDs:", docIDs)

	// Prepare the request body with the array of DocIDs
	requestBody, err := json.Marshal(docIDs)
	if err != nil {
		http.Error(w, "Failed to marshal request body", http.StatusInternalServerError)
		return
	}

	dbName := locality + "_model_updates"

	// Prepare the URL with the dbName as a query parameter
	dbURL := "http://localhost:50051/db"
	data := url.Values{}
	data.Set("db", dbName)
	req, err := http.NewRequest("GET", dbURL, bytes.NewBuffer(requestBody))
	if err != nil {
		http.Error(w, "Failed to create request", http.StatusInternalServerError)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.URL.RawQuery = data.Encode()

	// Send the request to /db
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "Failed to send request to /db", http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	// Read the response from /db
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		http.Error(w, "Failed to read response from /db", http.StatusInternalServerError)
		return
	}

	if resp.StatusCode != http.StatusOK {
		http.Error(w, string(respBody), resp.StatusCode)
		return
	}

	// Parse the response from /db
	var documents []map[string]interface{}
	if err := json.Unmarshal(respBody, &documents); err != nil {
		http.Error(w, "Failed to parse response from /db", http.StatusInternalServerError)
		return
	}

	// Extract values from "modelupdate" key
	var modelUpdatesList []map[string]interface{}
	for _, doc := range documents {
		if modelUpdate, ok := doc["state_dict"].(map[string]interface{}); ok {
			modelUpdatesList = append(modelUpdatesList, modelUpdate)
		}
	}

	// Print the length of modelUpdatesList
	log.Printf("Returned %d updates.\n", len(modelUpdatesList))

	// Return the extracted values as JSON
	response, err := json.Marshal(modelUpdatesList)
	if err != nil {
		http.Error(w, "Failed to marshal response", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(response)
	log.Printf("--Query Request Completed--")
}
