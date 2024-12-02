# model/nnmodel.py

from .models import VideoRecommendationModel
from .modeltrainer import ModelTrainer

import json
import torch
from torch.utils.data import DataLoader
import tenseal as ts
import os
import base64
import random
import hashlib
import ezkl
import asyncio

class NNModel:
    def __init__(self, input_dim: int, loss_func: torch.nn.Module, optimizer_class: torch.optim.Optimizer, optimizer_params: dict[str, any], client_id: str):
        self.__client_id = client_id
        self.model = VideoRecommendationModel(input_dim)
        self.loss_func = loss_func
        self.optimizer = optimizer_class(self.model.parameters(), **optimizer_params)
        self.__trainer = ModelTrainer(self.model, self.loss_func, self.optimizer)
        self.__modelupdate = None
        self.__encryptedupdate = None
        contextpath = os.path.join(os.path.dirname(__file__), "tenseal_context")
        with open(contextpath, 'rb') as f:
            self.__context = ts.context_from(f.read())

    def train(self, num_epochs: int, train_loader: DataLoader, test_loader: DataLoader) -> tuple[float, float]:
        print("\n--Model Training Initiated--\n")
        for epoch in range(num_epochs):
            train_loss, train_accuracy = self.__trainer.train(train_loader)
            test_loss, test_accuracy = self.__trainer.evaluate(test_loader)
            print(f"Epoch {epoch+1}/{num_epochs}, Train Loss: {train_loss:.4f}, Train Accuracy: {train_accuracy:.4f}, Test Loss: {test_loss:.4f}, Test Accuracy: {test_accuracy:.4f}")
        print("\n--Model Training Completed--")
        self.__generateModelUpdate()
        return train_accuracy, test_accuracy

    def evaluate(self, test_loader: DataLoader) -> tuple[float, float]:
        return self.__trainer.evaluate(test_loader)
    
    def __generateModelUpdate(self) -> None:
        # initializing empty encrypted state dict
        self.__modelupdate = {'participant_id': self.__client_id, 'state_dict': self.model.state_dict()}
        self.__encryptUpdate()

    def extractModelUpdate(self, encrypted: bool) -> dict[str, any]:
        if encrypted:
            return self.__encryptedupdate
        else:
            return self.__modelupdate
    
    def saveLocally(self, filepath: str) -> None:
        update_path = filepath + ".pth"
        torch.save(self.__modelupdate, update_path)
        print(f"\nModel Update Saved in: {update_path}")
        encrypted_update_path = filepath + "_enc.pth"
        torch.save(self.__encryptedupdate, encrypted_update_path)
        print(f"Encrypted Model Update Saved in: {encrypted_update_path}")
    
    def updateModel(self, l_update: dict[str, any], g_update: dict[str, any]) -> None:
        if g_update:
            print("Updating model weights with global update")
            model_weights = [0.7, 0.3]
            new_state_dict = {}
            for i, state_dict in enumerate((l_update, g_update)):
                # Aggregate each parameter
                for key, value in state_dict.items():
                    value['encrypted_data'] = ts.ckks_vector_from(self.__context, base64.b64decode(value['encrypted_data'])) * model_weights[i]
                    if key not in new_state_dict:
                        new_state_dict[key] = value
                    else:
                        new_state_dict[key]['encrypted_data'] += value['encrypted_data']
            new_state_dict = self.__decryptUpdate(new_state_dict)
        else:
            print("No global model found. Recommendations will now be based on local updates only.")
            new_state_dict = l_update

        self.model.load_state_dict(new_state_dict)
        
    def __encryptTensor(self, tensor: torch.Tensor) -> ts.CKKSTensor:
        return ts.ckks_vector(self.__context, tensor.flatten().tolist())
    
    def __encryptUpdate(self) -> None:
        self.__encryptedupdate = {'participant_id': self.__client_id, 'state_dict': {}}
        # for loop to encrypt tensor
        for key, value in self.__modelupdate['state_dict'].items():
            # Encrypt the weight tensors
            encrypted_value = self.__encryptTensor(value)
            # Serialize the encrypted value
            serialized_encrypted_value = base64.b64encode(encrypted_value.serialize()).decode('utf-8')
            # Adding the encrypted tensors back to the model update
            self.__encryptedupdate['state_dict'][key] = {
                'encrypted_data': serialized_encrypted_value,
                'original_shape': list(value.shape)
            }

    def __decryptTensor(self, tensor: ts.CKKSTensor, original_shape: list[int]) -> torch.Tensor:
        decrypted = torch.tensor(tensor.decrypt())
        return decrypted.reshape(original_shape)
    
    def __decryptUpdate(self, state_dict: dict[str, any]) -> dict[str, torch.Tensor]:
        decrypted_state_dict = {}
        
        for key, value in state_dict.items():
            original_shape = torch.Size(value['original_shape'])
            decrypted_state_dict[key] = self.__decryptTensor(value['encrypted_data'], original_shape)
        
        return decrypted_state_dict
    
    def __generateHash(self) -> dict[str, str]:
        # Convert the dictionary to a canonical JSON string
        canonical_json = json.dumps(self.__encryptedupdate['state_dict'], sort_keys=True)
        salt = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyz', k=random.randint(16, 32)))
        
        # Create a salted hash
        hasher = hashlib.sha256()
        hasher.update((canonical_json + salt).encode('utf-8'))
        gen_hash = hasher.hexdigest()
        
        return {'salt':salt, 'hashvalue':gen_hash}
    
    def __generateZKP(self, X_test: DataLoader) -> dict[str, any]:
        # set the file paths
        paths = {
            'model_path': 'network.onnx', 
            'compiled_model_path': 'network.compiled',
            'pk_path': 'test.pk',
            'vk_path': 'test.vk',
            'settings_path': 'settings.json',
            'witness_path': 'witness.json',
            'cal_path': "calibration.json",
            'data_path': "input.json",
            'temp_proof_path': "temp_proof.pf"
        }
        for key in paths:
            paths[key] = os.path.join(os.path.dirname(__file__), paths[key])
        
        # define asynchronous function for setting calibration
        async def cal_set(data_path, model_path, settings_path):
            await ezkl.calibrate_settings(data_path, model_path, settings_path, "resources")
            
        # define asynchronous function for generating srs
        async def srs(settings_path):
            await ezkl.get_srs(settings_path)
        
        # define asynchronous function to generate witness
        async def witness(data_path, compiled_model_path, witness_path):
            await ezkl.gen_witness(data_path, compiled_model_path, witness_path)

        # prepare input data
        x = torch.tensor(X_test[0])
        x = x.to(torch.float32).reshape(1, X_test.shape[1])

        #Run Model in Eval Mode
        self.model.eval()
        # Export the model into an onnx file; outputs into 'model_path'
        torch.onnx.export(self.model,              # model being run
                        x,                         # model input (or a tuple for multiple inputs)
                        paths['model_path'],       # where to save the model (can be a file or file-like object)
                        export_params=True,        # store the trained parameter weights inside the model file
                        opset_version=10,          # the ONNX version to export the model to
                        do_constant_folding=True,  # whether to execute constant folding for optimization
                        input_names = ['input'],   # the model's input names
                        output_names = ['output'], # the model's output names
                        dynamic_axes = {'input' : {0 : 'batch_size'},    # variable length axes
                                        'output' : {0 : 'batch_size'}})

        # generate setings using 'model_path'; outputs settings into 'settings_path'
        res = ezkl.gen_settings(paths['model_path'], paths['settings_path'])
        assert res == True

        # prepare data for setting calibration
        data_array = ((x).detach().numpy()).reshape([-1]).tolist()
        data = dict(input_data = [data_array])
        
        # Serialize data into file:
        json.dump(data, open(paths['data_path'], 'w'))
        # Serialize data into file:
        json.dump(data, open(paths['cal_path'], 'w'))
        # Run the calibration function; makes changes to 'settings_path' 
        asyncio.run(cal_set(paths['cal_path'], paths['model_path'], paths['settings_path']))

        # run compile function to compile model circuit; outputs into file 'compiled_model_path'
        res = ezkl.compile_circuit(paths['model_path'], paths['compiled_model_path'], paths['settings_path'])
        assert res == True

        # Run the function to get srs
        asyncio.run(srs(paths['settings_path']))

        # Generate the Witness for the proof; outputs in the 'witness_path' file
        asyncio.run(witness(paths['data_path'], paths['compiled_model_path'], paths['witness_path']))
        
        # mock testing of witness with original compiled model
        res = ezkl.mock(paths['witness_path'], paths['compiled_model_path'])
        assert res == True

        # generate the verification key and proving key from compiled model path; outputs in 'vk_path' and 'pk_path'
        res = ezkl.setup(paths['compiled_model_path'], paths['vk_path'], paths['pk_path'])
        assert res == True
        
        # Generate ZK proof using witness, compiled model and proving key; outputs in 'temp_proof_path'
        res = ezkl.prove(paths['witness_path'], paths['compiled_model_path'], paths['pk_path'], paths['temp_proof_path'], "single")
    
        # extract contents of the 'vk_path'
        with open(paths['vk_path'], 'rb') as f:
            vk_contents = base64.b64encode(f.read()).decode('utf-8')
        
        # extract contents of the 'settings_path'
        with open(paths['settings_path'], 'r') as f:
            settingsjson = json.load(f)
        
        # extract contents of the 'temp_proof_path'
        with open(paths['temp_proof_path'], 'r') as f:
            zk_proof = json.load(f)
            
        for key in paths:
            os.remove(paths[key])
        
        return {'vk_contents': vk_contents, 'settingsjson': settingsjson, 'zk_proof': zk_proof}
        
    def generateAndAttachProof(self, X_test: DataLoader) -> dict[str, any]:
        print("\n--Generating Proof for Sending Model Update--\n")
        # extract model update state dict
        modelupdate = self.__encryptedupdate
        # generate ZKP
        zkproof = self.__generateZKP(X_test)
        #generate hash
        hashedupdate = self.__generateHash()
        
        proof = {}
        for content in (zkproof, hashedupdate):
            for key, value in content.items():
                proof[key] = value
        
        modelupdate['proof'] = proof
        print("--Proof Generated and Attached--\n")

        return modelupdate