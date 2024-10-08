from flask import Flask, jsonify, request
import requests
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Solana Devnet RPC URL
SOLANA_RPC_URL = "https://api.devnet.solana.com"

def fetch_nfts(wallet_address):
    """Fetch NFTs stored in a Solana wallet on Devnet."""
    url = f"{SOLANA_RPC_URL}"
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
        return response.json()
    except Exception as e:
        logging.error(f"Error fetching NFTs: {e}")
        return None

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
            nfts.append({'mint': mint_address})

        return jsonify({
            'wallet': wallet_address,
            'nfts': nfts
        })

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'Error fetching NFTs'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
