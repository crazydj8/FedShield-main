# requesthandler/requesthandler.py

import json

from .api import Api

class RequestHandler():
    def __init__(self, agg_id: str):
        self.__agg_id = agg_id
        self.__apiip = "http://localhost:50051"
        self.__api = Api(self.__apiip)

    def storeModelUpdates(self, model_update: dict[str, any], locality: str) -> None:
        print(f"Aggregator {self.__agg_id} sent POST Request")
        self.__api.send_post_request(model_update, locality)
        
    def retrieveModelUpdates(self, locality: str) -> list[dict[str, any]]:
        record = self.__api.send_get_request(locality)
        updates_list = json.loads(record.strip())
        print(f"Retrieved {len(updates_list)} Model Updates.") 
        
        return updates_list