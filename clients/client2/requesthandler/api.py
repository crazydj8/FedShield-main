# requesthandler/api.py

import requests

class Api():
    def __init__(self, ip: str):
        self.__ip = ip

    def send_post_request(self, model_update: dict[str, any], locality: str) -> None:
        url = self.__ip + "/verify"
        
        params = {
            'locality': locality,
            'zkp': True
        }
        
        response = requests.post(url, params=params, json=model_update)
        # response.raise_for_status()  # Raise an exception for HTTP errors
        print(response.text)
        
    # Function to send a GET request
    def send_get_request(self, locality: str) -> str:
        url = self.__ip + "/query"
        
        params = {
            "locality": locality,
            "args": ""
        }
        
        response = requests.get(url, params=params)
        # response.raise_for_status()
        return response.text
