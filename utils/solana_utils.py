import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import config

logger = logging.getLogger(__name__)

LAMPORTS_PER_SOL = 1_000_000_000


class SolanaClient:
    """Utility class for Solana RPC interactions"""

    def __init__(self):
        self.rpc_url = config.SOLANA_RPC_URL

    async def verify_transaction(
        self,
        tx_signature: str,
        expected_amount: float,
        to_wallet: str,
        from_wallet: str = None,
    ) -> bool:
        """
        Verify a SOL transfer transaction on Solana blockchain.

        Args:
            tx_signature: Transaction hash/signature
            expected_amount: Expected SOL amount (in SOL, not lamports)
            to_wallet: Expected recipient wallet address
            from_wallet: (optional) Expected sender wallet

        Returns:
            True if transaction is valid and verified, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [
                        tx_signature,
                        {"encoding": "json", "maxSupportedTransactionVersion": 0}
                    ]
                }
                headers = {"Content-Type": "application/json"}

                async with session.post(
                    self.rpc_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:

                    if resp.status != 200:
                        logger.error(f"RPC error: {resp.status}")
                        return False

                    data = await resp.json()

                    if 'result' not in data or data['result'] is None:
                        logger.warning(f"Transaction {tx_signature} not found or failed")
                        return False

                    tx_data = data['result']

                    # Controlla che la tx sia confermata
                    if not tx_data.get('blockTime'):
                        logger.warning(f"Transaction {tx_signature} not yet confirmed")
                        return False

                    # Controlla che non sia troppo vecchia (max 1 ora)
                    tx_time = datetime.fromtimestamp(tx_data['blockTime'])
                    if datetime.now() - tx_time > timedelta(hours=1):
                        logger.warning(f"Transaction {tx_signature} is too old")
                        return False

                    # Controlla che non ci siano errori
                    meta = tx_data.get('meta', {})
                    if meta.get('err') is not None:
                        logger.warning(f"Transaction {tx_signature} has errors: {meta['err']}")
                        return False

                    # Recupera gli account coinvolti
                    account_keys = (
                        tx_data.get('transaction', {})
                        .get('message', {})
                        .get('accountKeys', [])
                    )

                    # Controlla che il destinatario sia nell'elenco degli account
                    if to_wallet not in account_keys:
                        logger.warning(
                            f"Recipient {to_wallet} not found in transaction accounts"
                        )
                        return False

                    # Calcola il delta SOL ricevuto dal destinatario
                    try:
                        to_index = account_keys.index(to_wallet)
                        pre_balances = meta.get('preBalances', [])
                        post_balances = meta.get('postBalances', [])

                        if to_index >= len(pre_balances) or to_index >= len(post_balances):
                            logger.warning("Balance arrays shorter than expected")
                            return False

                        received_lamports = post_balances[to_index] - pre_balances[to_index]
                        received_sol = received_lamports / LAMPORTS_PER_SOL

                        # Tolleranza 1% per eventuali fee/arrotondamenti
                        tolerance = expected_amount * 0.01
                        if received_sol < (expected_amount - tolerance):
                            logger.warning(
                                f"Amount mismatch: expected {expected_amount} SOL, "
                                f"got {received_sol:.6f} SOL"
                            )
                            return False

                    except (ValueError, IndexError) as e:
                        logger.error(f"Error parsing balances: {e}")
                        return False

                    logger.info(
                        f"✅ Transaction {tx_signature} verified — "
                        f"{received_sol:.4f} SOL received"
                    )
                    return True

        except Exception as e:
            logger.error(f"Error verifying transaction {tx_signature}: {str(e)}")
            return False
