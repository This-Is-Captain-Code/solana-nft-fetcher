from flask import Flask, jsonify, request
import requests
from flask_cors import CORS
import logging
from solana.rpc.async_api import AsyncClient
from solana.publickey import PublicKey
import base64
import struct

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Solana Devnet RPC URL
SOLANA_RPC_URL = "https://api.devnet.solana.com"
METAPLEX_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"  # Metaplex Token Metadata Program ID


def fetch_nfts(wallet_address):
    """Fetch NFTs stored in a Solana wallet on Devnet."""
    url = SOLANA_RPC_URL
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            wallet_address,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"}
        ]
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses
        logging.info(f"Response from Solana API: {response.json()}")
        return response.json()
    except Exception as e:
        logging.error(f"Error fetching NFTs for wallet {wallet_address}: {e}")
        return None


def fetch_metaplex_metadata(mint_address):
    """Fetch metadata for an NFT using Metaplex Token Metadata Program."""
    try:
        mint_pubkey = PublicKey(mint_address)
        metadata_pubkey, _ = PublicKey.find_program_address(
            [b'metadata', bytes(PublicKey(METAPLEX_PROGRAM_ID)), bytes(mint_pubkey)],
            PublicKey(METAPLEX_PROGRAM_ID)
        )

        # Prepare request payload to get account info
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                str(metadata_pubkey),
                {"encoding": "base64"}
            ]
        }
        headers = {"Content-Type": "application/json"}
        
        # Make the request
        response = requests.post(SOLANA_RPC_URL, json=payload, headers=headers)
        response.raise_for_status()

        account_info = response.json()
        logging.info(f"Metadata response for mint {mint_address}: {account_info}")

        # Decode base64 metadata if available
        if account_info.get('result') and account_info['result']['value']:
            metadata_base64 = account_info['result']['value']['data'][0]
            metadata_bytes = base64.b64decode(metadata_base64)

            # Parsing the metadata based on Metaplex Token Metadata schema
            parsed_metadata = parse_metadata(metadata_bytes)
            return parsed_metadata
        else:
            logging.warning(f"No metadata found for mint {mint_address}.")
            return None

    except Exception as e:
        logging.error(f"Error fetching Metaplex metadata for mint {mint_address}: {e}")
        return None
    
def parse_metadata(metadata_bytes):
    """Parses the binary Metaplex metadata."""
    # Example of basic parsing (you would adjust based on the Metaplex schema)
    name_length = struct.unpack("<I", metadata_bytes[32:36])[0]
    name = metadata_bytes[36:36+name_length].decode('utf-8', errors='ignore')

    # Continue parsing other fields like URI, symbol, etc.
    uri_length = struct.unpack("<I", metadata_bytes[68:72])[0]  # Adjust offset accordingly
    uri = metadata_bytes[72:72+uri_length].decode('utf-8', errors='ignore')

    return {
        'name': name,
        'uri': uri
    }


@app.route('/get_nfts', methods=['GET'])
def get_nfts():
    """API endpoint to get NFTs stored in a Solana Devnet wallet."""
    wallet_address = request.args.get('wallet')

    if not wallet_address:
        return jsonify({'error': "Wallet address is required."}), 400

    try:
        nfts_response = fetch_nfts(wallet_address)
        
        if nfts_response is None or 'result' not in nfts_response:
            return jsonify({'error': 'Error fetching NFTs from the Solana API'}), 500

        nfts = []
        for nft in nfts_response['result']['value']:
            mint_address = nft['account']['data']['parsed']['info']['mint']

            # Fetch Metaplex metadata for the NFT
            metadata = fetch_metaplex_metadata(mint_address)
            nfts.append({'mint': mint_address, 'metadata': metadata})

        return jsonify({
            'wallet': wallet_address,
            'nfts': nfts
        })

    except Exception as e:
        logging.error(f"Error processing request for wallet {wallet_address}: {str(e)}")
        return jsonify({'error': 'Error fetching NFTs'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
