import base58
from solana.rpc.api import Client
from solana.publickey import PublicKey
from solana.rpc.types import MemcmpOpts

METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"

# Function to derive the metadata address
def get_metadata_pda(mint_address):
    mint_publickey = PublicKey(mint_address)
    metadata_seed = [
        b'metadata',
        PublicKey(METADATA_PROGRAM_ID).to_bytes(),
        mint_publickey.to_bytes(),
    ]
    metadata_pda, _ = PublicKey.find_program_address(metadata_seed, PublicKey(METADATA_PROGRAM_ID))
    return metadata_pda

# Fetch Metaplex metadata using the metadata address
def fetch_metaplex_metadata(mint_address):
    try:
        metadata_pda = get_metadata_pda(mint_address)
        client = Client(SOLANA_RPC_URL)
        metadata_account_info = client.get_account_info(metadata_pda)

        if not metadata_account_info or 'result' not in metadata_account_info:
            logging.error(f"No metadata found for mint address: {mint_address}")
            return None

        metadata_data = metadata_account_info['result']['value']['data']
        metadata_decoded = base58.b58decode(metadata_data).decode('utf-8')
        
        logging.info(f"Metadata for mint {mint_address}: {metadata_decoded}")
        return metadata_decoded
    except Exception as e:
        logging.error(f"Error fetching Metaplex metadata: {str(e)}")
        return None

# Extend the current Flask endpoint
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
            
            # Fetch Metaplex metadata for each mint address
            metadata = fetch_metaplex_metadata(mint_address)
            nfts.append({
                'mint': mint_address,
                'metadata': metadata
            })

        return jsonify({
            'wallet': wallet_address,
            'nfts': nfts
        })

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'Error fetching NFTs'}), 500
