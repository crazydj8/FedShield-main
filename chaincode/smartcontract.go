package main

import (
	"encoding/json"
	"fmt"
	"log"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// SmartContract provides functions for managing the ledger
type SmartContract struct {
	contractapi.Contract
}

// ModelUpdate defines the structure of a value stored on the ledger
type ModelUpdate struct {
	DocType       string `json:"docType"`
	ParticipantID string `json:"ParticipantID"`
	DocID         string `json:"DocID"`
}

// InitLedger initializes the ledger with a default value
func (s *SmartContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	defaultValue := ModelUpdate{
		DocType:       "modelUpdate",
		ParticipantID: "default",
		DocID:         "0",
	}

	valueJSON, err := json.Marshal(defaultValue)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState("default", valueJSON)
}

// StoreModel stores a new value associated with a client ID
func (s *SmartContract) StoreUpdate(ctx contractapi.TransactionContextInterface, participantId string, docID string) error {
	// Ensure the docID is stored as a string
	update := ModelUpdate{
		DocType:       "modelUpdate",
		ParticipantID: participantId,
		DocID:         docID,
	}

	updateJSON, err := json.Marshal(update)
	if err != nil {
		return err
	}

	return ctx.GetStub().PutState(participantId, updateJSON)
}

// QueryModel retrieves all values stored on the ledger
func (s *SmartContract) QueryUpdate(ctx contractapi.TransactionContextInterface) ([]*ModelUpdate, error) {
	queryString := fmt.Sprintf(`{"selector":{"docType":"modelUpdate"}}`)
	return getQueryResultForQueryString(ctx, queryString)
}

// QueryByParticipantID retrieves values for a specific participant
func (s *SmartContract) QueryByParticipantID(ctx contractapi.TransactionContextInterface, participantId string) ([]*ModelUpdate, error) {
	queryString := fmt.Sprintf(`{"selector":{"docType":"modelUpdate","ParticipantID":"%s"}}`, participantId)
	return getQueryResultForQueryString(ctx, queryString)
}

// getQueryResultForQueryString executes the passed in query string.
func getQueryResultForQueryString(ctx contractapi.TransactionContextInterface, queryString string) ([]*ModelUpdate, error) {
	resultsIterator, err := ctx.GetStub().GetQueryResult(queryString)
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()

	var results []*ModelUpdate
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}

		var update ModelUpdate
		err = json.Unmarshal(queryResponse.Value, &update)
		if err != nil {
			return nil, err
		}
		results = append(results, &update)
	}

	return results, nil
}

// main function starts up the chaincode in the container during instantiate
func main() {
	chaincode, err := contractapi.NewChaincode(new(SmartContract))
	if err != nil {
		log.Panicf("Error creating smart contract: %v", err)
	}

	if err := chaincode.Start(); err != nil {
		log.Panicf("Error starting smart contract: %v", err)
	}
}
