package web

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/url"
)

// Verify handles the verification requests.
func (setup OrgSetup) Verify(w http.ResponseWriter, r *http.Request) {
	log.Printf("--Verify Request Initiaited--")

	// Parse JSON body
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Unable to read request body", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	var payload map[string]interface{}
	if err := json.Unmarshal(body, &payload); err != nil {
		http.Error(w, "Invalid JSON format", http.StatusBadRequest)
		return
	}

	// Extract form values
	queryParams := r.URL.Query()
	locality := queryParams.Get("locality")
	zkp := queryParams.Get("zkp")

	// Validate input data
	if locality == "" {
		http.Error(w, "Missing required parameters", http.StatusBadRequest)
		return
	}

	// Extract state_dict
	stateDict, ok := payload["state_dict"].(map[string]interface{})
	if !ok {
		http.Error(w, "Invalid state_dict format", http.StatusBadRequest)
		return
	}

	// Extract proof
	proof, ok := payload["proof"].(map[string]interface{})
	if !ok {
		http.Error(w, "Invalid proof format", http.StatusBadRequest)
		return
	}

	// Create a new JSON object
	verify := map[string]interface{}{
		"state_dict": stateDict,
		"proof":      proof,
	}

	// Marshal the new JSON object into a JSON string
	verifyJSON, err := json.Marshal(verify)
	if err != nil {
		http.Error(w, "Error creating JSON", http.StatusInternalServerError)
		return
	}

	verifyData := url.Values{}
	verifyData.Set("zkp", zkp)

	verifyURL := "http://localhost:5000/verify"
	verifyReq, err := http.NewRequest("POST", verifyURL, bytes.NewReader(verifyJSON))
	if err != nil {
		http.Error(w, "Failed to create request", http.StatusInternalServerError)
		return
	}

	verifyReq.Header.Set("Content-Type", "application/json")
	verifyReq.URL.RawQuery = verifyData.Encode()

	verifyClient := &http.Client{}
	verifyResp, err := verifyClient.Do(verifyReq)
	if err != nil {
		http.Error(w, "Failed to send request to /verify", http.StatusInternalServerError)
		return
	}
	defer verifyResp.Body.Close()

	// Read response from /verify
	verifyRespBody, err := io.ReadAll(verifyResp.Body)
	if err != nil {
		http.Error(w, "Failed to read response from /verify", http.StatusInternalServerError)
		return
	}

	// Parse the verification response
	var verifyRespData map[string]bool
	if err := json.Unmarshal(verifyRespBody, &verifyRespData); err != nil {
		http.Error(w, "Invalid response format from /verify", http.StatusInternalServerError)
		return
	}

	// Check the verification result
	if !verifyRespData["verification"] {
		log.Printf("VERIFICATION RESULT : FAILURE\n")
		log.Printf("--Verify Request Completed--")
		http.Error(w, "Verification failed", http.StatusUnauthorized)
		return
	} else {
		log.Printf("VERIFICATION RESULT : SUCCESS\n")
	}

	// Extract participant_id
	participantID, ok := payload["participant_id"].(string)
	if !ok {
		http.Error(w, "Invalid participant_id format", http.StatusBadRequest)
		return
	}

	// Create a new JSON object
	modelUpdate := map[string]interface{}{
		"participant_id": participantID,
		"state_dict":     stateDict,
	}

	// Marshal the new JSON object into a JSON string
	modelUpdateJSON, err := json.Marshal(modelUpdate)
	if err != nil {
		http.Error(w, "Error creating JSON", http.StatusInternalServerError)
		return
	}

	// Define parameters
	chaincodeID := "mycc"
	function := "StoreUpdate"

	log.Printf("--Verify Request Completed--")

	// Prepare form-encoded data
	data := url.Values{}
	data.Set("locality", locality)
	data.Set("chaincodeid", chaincodeID)
	data.Set("function", function)
	data.Add("args", "")

	invokeURL := "http://localhost:50051/invoke"
	req, err := http.NewRequest("POST", invokeURL, bytes.NewReader(modelUpdateJSON))
	if err != nil {
		http.Error(w, "Failed to create request", http.StatusInternalServerError)
		return
	}

	req.Header.Set("Content-Type", "application/json")
	req.URL.RawQuery = data.Encode()

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "Failed to send request to /invoke", http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	// Read response from /invoke
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		http.Error(w, "Failed to read response from /invoke", http.StatusInternalServerError)
		return
	}

	// Respond with the response from /invoke
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	w.Write(respBody)
}
