from flask import Flask, jsonify, request
import requests
from flask_cors import CORS
import logging
import base64
from solana.publickey import PublicKey
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
import base58

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Solana Devnet RPC URL
SOLANA_RPC_URL = "https://api.devnet.solana.com"
METAPLEX_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"  # Metaplex Metadata program ID

client = Client(SOLANA_RPC_URL)

def fetch_nfts(wallet_address):
    """Fetch NFTs stored in a Solana wallet on Devnet."""
    url = f"{SOLANA_RPC_URL}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            wallet_address,  # Use the original Base58 address here
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
        logging.error(f"Error fetching NFTs: {e}")
        return None

def get_metadata_account(mint_address):
    """Derive the metadata account associated with the NFT's mint address."""
    seed = [
        b"metadata",
        PublicKey(METAPLEX_PROGRAM_ID).to_bytes(),
        PublicKey(mint_address).to_bytes()
    ]
    metadata_pubkey = PublicKey.find_program_address(seed, PublicKey(METAPLEX_PROGRAM_ID))[0]
    return str(metadata_pubkey)

def fetch_metadata(mint_address):
    """Fetch Metaplex metadata for the given mint address."""
    metadata_account = get_metadata_account(mint_address)
    
    url = f"{SOLANA_RPC_URL}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [
            metadata_account,
            {"encoding": "base64"}
        ]
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()['result']['value']
        if result:
            account_data = base64.b64decode(result['data'][0])
            logging.info(f"Metadata account raw data: {account_data}")
            # Parse the account data into meaningful Metaplex metadata fields
            return decode_metadata(account_data)
        else:
            logging.warning(f"No metadata found for mint: {mint_address}")
            return None
    except Exception as e:
        logging.error(f"Error fetching metadata: {e}")
        return None

def decode_metadata(account_data):
    """Decode the raw metadata into structured data."""
    # You'll need to implement the decoding here. You can use Metaplex libraries
    # or custom code to parse the fields like name, uri, symbol, creators, etc.
    # For now, we'll return a placeholder.
    metadata = {
        'name': 'Placeholder name',
        'uri': 'Placeholder URI',
        'symbol': 'Placeholder symbol',
        # Add more fields as needed
    }
    return metadata

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
            metadata = fetch_metadata(mint_address)
            nfts.append({'mint': mint_address, 'metadata': metadata})

        return jsonify({
            'wallet': wallet_address,
            'nfts': nfts
        })

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'Error fetching NFTs'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
