package web

import (
	"bytes"
	"encoding/json"
	"fmt"
	"github.com/joho/godotenv"
	"io/ioutil"
	"log"
	"net/http"
	"os"
)

// DBConnector holds the CouchDB connection details.
type DBConnector struct {
	CouchDBURL string
	Username   string
	Password   string
}

// NewDBConnector initializes a new DBConnector instance.
func NewDBConnector(ip string) *DBConnector {
	err := godotenv.Load()
	if err != nil {
		log.Fatalf("Error loading .env file")
	}
	return &DBConnector{
		CouchDBURL: ip,
		Username:   os.Getenv("COUCHDB_USERNAME"),
		Password:   os.Getenv("COUCHDB_PASSWORD"),
	}
}

// createDocument handles the creation of a document in CouchDB and returns the document ID.
func (db *DBConnector) createDocument(w http.ResponseWriter, r *http.Request) {
	var data map[string]interface{}
	err := json.NewDecoder(r.Body).Decode(&data)
	if err != nil {
		http.Error(w, "Invalid JSON format", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	dbname := r.URL.Query().Get("db")
	url := fmt.Sprintf("%s/%s", db.CouchDBURL, dbname)
	jsonData, err := json.Marshal(data)
	if err != nil {
		http.Error(w, "Failed to marshal JSON", http.StatusInternalServerError)
		return
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		http.Error(w, "Failed to create request", http.StatusInternalServerError)
		return
	}
	req.SetBasicAuth(db.Username, db.Password)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		http.Error(w, "Failed to send request", http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		http.Error(w, "Failed to read response", http.StatusInternalServerError)
		return
	}

	if resp.StatusCode != http.StatusCreated {
		http.Error(w, string(body), resp.StatusCode)
		return
	}

	var responseData map[string]interface{}
	if err := json.Unmarshal(body, &responseData); err != nil {
		http.Error(w, "Failed to unmarshal response", http.StatusInternalServerError)
		return
	}

	docID, ok := responseData["id"].(string)
	if !ok {
		http.Error(w, "Failed to retrieve document ID", http.StatusInternalServerError)
		return
	}

	log.Printf("Saved document in: %s, with document ID: %s\n", dbname, docID)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	w.Write([]byte(fmt.Sprintf(`{"id": "%s"}`, docID)))
}

// getDocument handles the retrieval of a document from CouchDB.
func (db *DBConnector) getDocument(w http.ResponseWriter, r *http.Request) {
	dbName := r.URL.Query().Get("db")
	var docIDs []string
	if err := json.NewDecoder(r.Body).Decode(&docIDs); err != nil {
		http.Error(w, "Invalid JSON format", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	var documents []map[string]interface{}
	for _, docID := range docIDs {
		url := fmt.Sprintf("%s/%s/%s", db.CouchDBURL, dbName, docID)
		req, err := http.NewRequest("GET", url, nil)
		if err != nil {
			http.Error(w, "Failed to create request", http.StatusInternalServerError)
			return
		}
		req.SetBasicAuth(db.Username, db.Password)

		client := &http.Client{}
		resp, err := client.Do(req)
		if err != nil {
			http.Error(w, "Failed to send request", http.StatusInternalServerError)
			return
		}
		defer resp.Body.Close()

		body, err := ioutil.ReadAll(resp.Body)
		if err != nil {
			http.Error(w, "Failed to read response", http.StatusInternalServerError)
			return
		}

		if resp.StatusCode != http.StatusOK {
			http.Error(w, string(body), resp.StatusCode)
			return
		}

		var document map[string]interface{}
		if err := json.Unmarshal(body, &document); err != nil {
			http.Error(w, "Failed to unmarshal response", http.StatusInternalServerError)
			return
		}

		// Print the document
		documents = append(documents, document)
	}

	response, err := json.Marshal(documents)
	if err != nil {
		http.Error(w, "Failed to marshal response", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write(response)
}

// handler routes the request to the appropriate method based on the HTTP method.
func (db *DBConnector) handler(w http.ResponseWriter, r *http.Request) {
	log.Printf("----DB Request (%s) Initiated----\n", r.Method)
	switch r.Method {
	case http.MethodPost:
		db.createDocument(w, r)
	case http.MethodGet:
		db.getDocument(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
	log.Printf("----DB Request (%s) Completed----\n", r.Method)
}
