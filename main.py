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

# Metaplex API for fetching NFT metadata
METAPLEX_API_URL = "https://api.devnet.metaplex.com"

async def get_nfts_from_wallet(wallet_address):
    """Fetch NFTs stored in a Solana wallet on Devnet."""
    async with AsyncClient(SOLANA_RPC_URL) as client:
        try:
            logging.info(f"Fetching NFTs for wallet: {wallet_address}")
            public_key = PublicKey(wallet_address)
            response = await client.get_token_accounts_by_owner(public_key, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"})
            token_accounts = response['result']['value']
            
            nfts = []
            for account in token_accounts:
                account_pubkey = account['pubkey']
                logging.info(f"Processing account: {account_pubkey}")
                # Fetch the token's metadata (Assuming standard SPL Token NFT format)
                account_data = account['account']['data']
                mint = account_data['parsed']['info']['mint']

                # Fetch NFT metadata from the Metaplex API or other sources
                nft_metadata = await fetch_nft_metadata(mint)
                if nft_metadata:
                    nfts.append(nft_metadata)
            
            return nfts

        except Exception as e:
            logging.error(f"Error fetching NFTs: {e}")
            return []

async def fetch_nft_metadata(mint_address):
    """Fetch NFT metadata using the Metaplex API or a custom API."""
    try:
        url = f"{METAPLEX_API_URL}/nfts/{mint_address}/metadata"
        response = requests.get(url)
        
        if response.status_code == 200:
            metadata = response.json()

            # Extract data from the metadata response
            nft_data = metadata.get('data', {})
            name = nft_data.get('name', 'Unnamed NFT')
            uri = nft_data.get('uri', '')  # The URL pointing to the actual NFT (could be the 3D model in this case)
            creators = nft_data.get('creators', [])
            seller_fee = nft_data.get('sellerFeeBasisPoints', 0)

            # Construct a response object for the NFT
            nft_info = {
                'name': name,
                'mint': metadata.get('mint', mint_address),  # Mint address
                'updateAuthority': metadata.get('updateAuthority', ''),
                'uri': uri,  # Could be a link to download the 3D model
                'sellerFeeBasisPoints': seller_fee,
                'creators': creators,
                'primarySaleHappened': metadata.get('primarySaleHappened', 0),
                'isMutable': metadata.get('isMutable', 1),
                'tokenStandard': metadata.get('tokenStandard', 0)
            }
            
            return nft_info
        else:
            logging.error(f"Error fetching metadata for mint: {mint_address}, status code: {response.status_code}")
            return None

    except Exception as e:
        logging.error(f"Error fetching metadata: {e}")
        return None


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
