package web

import (
	"fmt"
	"net/http"

	"github.com/hyperledger/fabric-gateway/pkg/client"
)

// OrgSetup contains organization's config to interact with the network.
type OrgSetup struct {
	OrgName      string
	MSPID        string
	CryptoPath   string
	CertPath     string
	KeyPath      string
	TLSCertPath  string
	PeerEndpoint string
	GatewayPeer  string
	Gateway      client.Gateway
}

// Serve starts http web server.
func Serve(setups OrgSetup) {
	dbConnector := NewDBConnector("http://localhost:5984")
	http.HandleFunc("/query", setups.Query)
	http.HandleFunc("/invoke", setups.Invoke)
	http.HandleFunc("/verify", setups.Verify)
	http.HandleFunc("/db", dbConnector.handler) // Add the new route here
	fmt.Println("Communicator is Listening on http://localhost:50051/...")
	if err := http.ListenAndServe(":50051", nil); err != nil {
		fmt.Println(err)
	}
}
