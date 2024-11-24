# aggregator/aggregator.py

import os
import base64
import torch
import tenseal as ts
import json
import random
import hashlib

class Aggregator():
    def __init__(self, agg_id: str):
        self.__agg_id = agg_id
        self.__global_update = {}
        contextpath = os.path.join(os.path.dirname(__file__), "tenseal_context")
        with open(contextpath, 'rb') as f:
            self.__context = ts.context_from(f.read())
    
    def aggregate(self, state_dicts: list[dict[str, any]]) -> dict[str, any]:
        print(f"Performing aggregation on {len(state_dicts)} model updates...")
        model_weights = [1/len(state_dicts) for i in range(len(state_dicts))]
        aggregated_state_dict = {}
        
        for i, state_dict in enumerate(state_dicts):
            print(f"Processing update {i+1}")
            for key, value in state_dict.items():
                value['encrypted_data'] = ts.ckks_vector_from(self.__context, base64.b64decode(value['encrypted_data'])) * model_weights[i]
                if key not in aggregated_state_dict:
                    aggregated_state_dict[key] = value
                else:
                    aggregated_state_dict[key]['encrypted_data'] += value['encrypted_data']
        
        aggregated_state_dict = {key: {'encrypted_data': base64.b64encode(value['encrypted_data'].serialize()).decode('utf-8'), 'original_shape': value['original_shape']} for key, value in aggregated_state_dict.items()}
        
        self.__global_update = {"participant_id": self.__agg_id, "state_dict": aggregated_state_dict}
        
        return self.__global_update
    
    def save_model_locally(self, filepath: str) -> None:
        torch.save(self.__global_update, filepath)
        print(f"Aggregated Model Update Saved in: {filepath}")
        print()
        
    def __generateHash(self) -> dict[str, str]:
        # Convert the dictionary to a canonical JSON string
        canonical_json = json.dumps(self.__global_update['state_dict'], sort_keys=True)
        salt = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=random.randint(16, 32)))
        
        # Create a salted hash
        hasher = hashlib.sha256()
        hasher.update((canonical_json + salt).encode('utf-8'))
        gen_hash = hasher.hexdigest()
        
        return {'salt':salt, 'hashvalue':gen_hash}    
    
    def generateAndAttachProof(self) -> dict[str, any]:
        print("\n--Generating Proof for Sending Model Update--\n")
        # extract model update state dict
        modelupdate = self.__global_update
        #generate hash
        hashedupdate = self.__generateHash()
        
        proof = {}
        for key, value in hashedupdate.items():
            proof[key] = value
        
        modelupdate['proof'] = proof
        print("--Proof Generated and Attached--\n")

        return modelupdate