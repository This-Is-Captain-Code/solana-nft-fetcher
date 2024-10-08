from flask import Flask, jsonify, request
import requests
from solana.rpc.async_api import AsyncClient
from solana.publickey import PublicKey
from flask_cors import CORS
import logging
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Solana Devnet RPC URL
SOLANA_RPC_URL = "https://api.devnet.solana.com"

# Metaplex API for fetching NFT metadata (replace with your actual endpoint if necessary)
METAPLEX_API_URL = "https://api.devnet.metaplex.com"  # Example URL, adjust as needed

async def fetch_nft_metadata(mint_address):
    """Fetch NFT metadata from the Metaplex API."""
    url = f"{METAPLEX_API_URL}/nft/{mint_address}/metadata"  # Placeholder URL, adjust accordingly
    response = requests.get(url)  # Replace with an async request if necessary
    if response.status_code == 200:
        return response.json()
    else:
        logging.warning(f"Metadata not found for mint address: {mint_address}")
        return None

async def get_nfts_from_wallet(wallet_address):
    """Fetch NFTs stored in a Solana wallet on Devnet."""
    async with AsyncClient(SOLANA_RPC_URL) as client:
        try:
            logging.info(f"Fetching NFTs for wallet: {wallet_address}")
            public_key = PublicKey(wallet_address)

            # Get token accounts by owner (wallet) and filter by the Token Program ID for SPL tokens
            response = await client.get_token_accounts_by_owner(
                public_key,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}
            )

            # Extract token accounts from the response
            token_accounts = response.get('result', {}).get('value', [])

            if not token_accounts:
                logging.info(f"No token accounts found for wallet: {wallet_address}")
                return []

            nfts = []
            for account in token_accounts:
                account_info = account['account']['data']['parsed']['info']
                mint_address = account_info.get('mint')

                if mint_address:
                    logging.info(f"Processing mint address: {mint_address}")
                    # Fetch NFT metadata using the Metaplex API or similar
                    nft_metadata = await fetch_nft_metadata(mint_address)
                    if nft_metadata:
                        nfts.append(nft_metadata)

            return nfts

        except Exception as e:
            logging.error(f"Error fetching NFTs: {e}")
            return []

@app.route('/get_nfts', methods=['GET'])
def get_nfts():
    """API endpoint to get NFTs stored in a Solana Devnet wallet."""
    wallet_address = request.args.get('wallet')

    if not wallet_address:
        return jsonify({'error': "Wallet address is required."}), 400

    try:
        # Run the async task in an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        nfts = loop.run_until_complete(get_nfts_from_wallet(wallet_address))

        return jsonify({
            'wallet': wallet_address,
            'nfts': nfts
        })

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'Error fetching NFTs'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
