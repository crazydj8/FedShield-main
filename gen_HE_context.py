#!/usr/bin/env python3

import os
import argparse
import tenseal as ts

def generate_keys(n: int) -> None:
    # Create TenSEAL context
    context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192, coeff_mod_bit_sizes=[40, 21, 21, 21, 21, 21, 21, 40])
    context.global_scale = 2**21
    context.generate_galois_keys()
    context.generate_relin_keys()
    serialized_context = context.serialize(save_public_key=True, save_secret_key=True, save_galois_keys=True,  save_relin_keys=True)
    
    curdir = os.path.dirname(__file__)
    for i in range(1, n+1):
        # Save the context to files
        clientpath = os.path.join(curdir, f"clients/client{i}/model/tenseal_context")
        with open(clientpath, "wb") as f:
            f.write(serialized_context)
    
    context.make_context_public()
    serialized_context = context.serialize(save_public_key=True, save_galois_keys=True,  save_relin_keys=True)
    aggpath = os.path.join(curdir, "aggregator/aggregator/tenseal_context")
    with open(aggpath, "wb") as f:
        f.write(serialized_context)

    print("Keys generated and saved.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate homomorphic encryption keys for clients.")
    parser.add_argument("num_clients", type=int, help="Total number of clients")
    args = parser.parse_args()
    
    generate_keys(args.num_clients)