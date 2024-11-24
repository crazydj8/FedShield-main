import base64
import hashlib
import json
import os
import tempfile
import ezkl

class Verifier():
    def __init__(self):
        pass

    def verify(self, proof_data: dict[str, any], zkp: bool) -> dict[str, bool]:
        # exctract state dict
        encrypted_state_dict = proof_data['state_dict']
        
        # extract hash values
        stored_hash = proof_data['proof']['hashvalue']
        stored_salt = proof_data['proof']['salt']
        
        # verify Hash
        try:
            hashresult = self.__verifyHash(encrypted_state_dict, stored_hash, stored_salt)
        except Exception as e:
            print(f"Error during verification: {e}")
            hashresult = False
        
        zkpresult = True
        if zkp:
            # extract proof contents
            zk_proof = proof_data['proof']['zk_proof']
            vk_contents = base64.b64decode(proof_data['proof']['vk_contents'])
            settingsjson = proof_data['proof']['settingsjson']
            # verify ZKP
            try:
                zkpresult = self.__verifyProof(zk_proof, vk_contents, settingsjson)
            except Exception as e:
                print(f"Error during verification: {e}")
                zkpresult = False
                
        # compute final result
        result = zkpresult and hashresult
        
        # create response
        resultjson = {'verification' : result}
        return resultjson
        
    def __verifyProof(self, proof: dict[str, any], verification_key: bytes, settings: dict[str, any]) -> bool:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_proof_file:
            temp_proof_path = temp_proof_file.name
            json.dump(proof, temp_proof_file)
        
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_vk_file:
            temp_vk_path = temp_vk_file.name
            temp_vk_file.write(verification_key)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_settings_file:
            temp_settings_path = temp_settings_file.name
            json.dump(settings, temp_settings_file)

        try:
            result = ezkl.verify(temp_proof_path, temp_settings_path, temp_vk_path)
        except RuntimeError as e:
            print(f"Error during ZK verification: {e}")
            result = False
        finally:
            os.remove(temp_proof_path)
            os.remove(temp_vk_path)
            os.remove(temp_settings_path)
            
        return result
    
    def __verifyHash(self, encrypted_state_dict: dict[str, any], hashvalue: str, salt: str) -> bool:
        canonical_json = json.dumps(encrypted_state_dict, sort_keys=True)
        hasher = hashlib.sha256()
        hasher.update((canonical_json + salt).encode('utf-8'))
        computed_hash = hasher.hexdigest()
        result = (computed_hash == hashvalue)
        return result