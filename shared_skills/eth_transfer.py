import os
from web3 import Web3

def transfer_eth(to_address: str, amount_eth: float) -> str:
    """Transfer ETH from the agent's wallet to a user's wallet."""
    rpc_url = os.environ.get("RPC_URL", "https://mainnet.infura.io/v3/YOUR_INFURA_KEY")
    private_key = os.environ.get("PRIVATE_KEY")

    if not private_key:
        return "Error: PRIVATE_KEY not found in environment."

    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network."

        account = w3.eth.account.from_key(private_key)
        from_address = account.address

        nonce = w3.eth.get_transaction_count(from_address)

        tx = {
            'nonce': nonce,
            'to': to_address,
            'value': w3.to_wei(amount_eth, 'ether'),
            'gas': 21000,
            'gasPrice': w3.eth.gas_price,
            'chainId': w3.eth.chain_id
        }

        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return f"Success: Transaction sent. Hash: {w3.to_hex(tx_hash)}"
    except Exception as e:
        return f"Error during ETH transfer: {e}"

def get_balance() -> str:
    """Get the ETH balance of the agent's wallet."""
    rpc_url = os.environ.get("RPC_URL", "")
    private_key = os.environ.get("PRIVATE_KEY")

    if not private_key:
        return "Error: PRIVATE_KEY not found in environment."

    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return "Error: Could not connect to Ethereum network."

        account = w3.eth.account.from_key(private_key)
        balance_wei = w3.eth.get_balance(account.address)
        balance_eth = w3.from_wei(balance_wei, 'ether')

        return f"Wallet Address: {account.address}\nBalance: {balance_eth} ETH"
    except Exception as e:
        return f"Error getting balance: {e}"
