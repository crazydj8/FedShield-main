# requesthandler/requesthandler.py

import json

from .api import Api

class RequestHandler():
    def __init__(self, client_id: str):
        self.__client_id = client_id
        self.__apiip = "http://localhost:50051"
        self.__api = Api(self.__apiip)

    def storeModelUpdates(self, model_update: dict[str, any], locality: str) -> None:
        print(f"Client {self.__client_id} sent POST Request\n")
        self.__api.send_post_request(model_update, locality)
        
    def retrieveModelUpdates(self, locality: str) -> list:
        record = self.__api.send_get_request(locality)
        updates_list = json.loads(record.strip())
        
        return updates_list