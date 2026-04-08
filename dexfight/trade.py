"""
Trade - Arbitrage execution
Adapted for X Layer with OKX Skills integration
"""

import asyncio
import logging

import web3dex
from config_xlayer import CHAIN

logger = logging.getLogger(__name__)


def price_impact_base(dex: web3dex.Dex, amount: float, in_token: str, out_token: str, middle_token: str = None):
    """
    Calculate price impact for buying (base -> token)
    Based on AMM constant product formula
    """
    liquidity_in = dex.liquidity_in(in_token, out_token, middle_token)
    liquidity_out = dex.liquidity_out(in_token, out_token, middle_token)

    if liquidity_in == 0:
        return 1.0

    price = liquidity_out / liquidity_in
    new_liquidity_in = liquidity_in + amount
    new_liquidity_out = (liquidity_in * liquidity_out) / new_liquidity_in
    new_price = new_liquidity_out / new_liquidity_in

    price_impact = (new_price - price) / price

    logger.debug(f"price_impact_base: amount={amount}, price={price}, new_price={new_price}, impact={price_impact}")
    return price_impact


def price_impact_token(dex: web3dex.Dex, amount: float, in_token: str, out_token: str, middle_token: str = None):
    """
    Calculate price impact for selling (token -> base)
    """
    liquidity_in = dex.liquidity_in(in_token, out_token, middle_token)
    liquidity_out = dex.liquidity_out(in_token, out_token, middle_token)

    if liquidity_in == 0:
        return 1.0

    price = liquidity_out / liquidity_in
    new_liquidity_out = liquidity_out + amount
    new_liquidity_in = (liquidity_in * liquidity_out) / new_liquidity_out
    new_price = new_liquidity_out / new_liquidity_in

    price_impact = (new_price - price) / price

    logger.debug(f"price_impact_token: amount={amount}, price={price}, new_price={new_price}, impact={price_impact}")
    return price_impact


def buy(dex: web3dex.Dex, token: str, amount: float, middle_token: str, wallet_address: str, private_key: str, nonce: int = None):
    """Execute buy order (USDC -> Token)"""
    tx = dex.swap_from_base_to_tokens(amount, token, wallet_address, middle_token, nonce=nonce, in_base=True)

    logger.info(f"Buy: {amount} USDC -> {token} on {dex.platform}")
    logger.debug(f"Transaction: {tx}")

    signed_tx = dex.sign_transaction(tx, private_key)
    tx_hash = dex.send_transaction(signed_tx)

    tx["hash"] = tx_hash
    return tx


def sell(dex: web3dex.Dex, token: str, amount: float, middle_token: str, wallet_address: str, private_key: str, nonce: int = None):
    """Execute sell order (Token -> USDC)"""
    tx = dex.swap_from_tokens_to_base(amount, token, wallet_address, middle_token, nonce=nonce, in_base=True)

    logger.info(f"Sell: {amount} {token} -> USDC on {dex.platform}")
    logger.debug(f"Transaction: {tx}")

    signed_tx = dex.sign_transaction(tx, private_key)
    tx_hash = dex.send_transaction(signed_tx)

    tx["hash"] = tx_hash
    return tx


def approve(dex: web3dex.Dex, token: str, wallet_address: str, private_key: str):
    """Approve token for trading"""
    tx = dex.approve(token=token, wallet_address=wallet_address)

    logger.info(f"Approving {token} on {dex.platform}")

    signed_tx = dex.sign_transaction(tx, private_key)
    tx_hash = dex.send_transaction(signed_tx)

    tx["hash"] = tx_hash

    if not dex.wait_transaction(tx_hash):
        raise Exception(f"Approve transaction failed: {tx_hash}")

    return tx


async def demo():
    """Demo function"""
    rpc = CHAIN["rpc_url"]

    dex0 = web3dex.UniswapV3(rpc)
    dex1 = web3dex.OKX(rpc)

    await main(
        wallet_address="0x0000000000000000000000000000000000000000",
        private_key="0x0000000000000000000000000000000000000000000000000000000000000000",
        dex0=dex0,
        dex1=dex1,
        amount=100,
        min_gap=0.01,
        path0_inToken=None,
        path0_outToken="0x...",
        path0_middleToken=dex0.token,
        path1_inToken=None,
        path1_outToken="0x...",
        path1_middleToken=dex1.token,
    )


async def main(
    wallet_address: str,
    private_key: str,
    dex0: web3dex.Dex,
    dex1: web3dex.Dex,
    amount: float,
    min_gap: float,
    path0_inToken,
    path0_outToken,
    path0_middleToken,
    path1_inToken,
    path1_outToken,
    path1_middleToken
):
    """Main arbitrage execution function"""

    logger.info(f"Starting arbitrage: {dex0.platform} vs {dex1.platform}")
    logger.info(f"Amount: {amount} USDC")

    # Get liquidity info
    logger.info(f"{dex0.platform}: liquidity_in={dex0.liquidity_in(path0_inToken, path0_outToken, path0_middleToken)}")
    logger.info(f"{dex0.platform}: liquidity_out={dex0.liquidity_out(path0_inToken, path0_outToken, path0_middleToken)}")
    logger.info(f"{dex1.platform}: liquidity_in={dex1.liquidity_in(path1_inToken, path1_outToken, path1_middleToken)}")
    logger.info(f"{dex1.platform}: liquidity_out={dex1.liquidity_out(path1_inToken, path1_outToken, path1_middleToken)}")

    # Get reserve ratios
    reserve0 = dex0.reserve_ratio(path0_inToken, path0_outToken, path0_middleToken)
    reserve1 = dex1.reserve_ratio(path1_inToken, path1_outToken, path1_middleToken)

    logger.info(f"Reserve ratio: {dex0.platform}={reserve0}, {dex1.platform}={reserve1}")

    # Determine which DEX has lower/higher price
    if reserve0 < reserve1:
        (dex_low, dex_high) = (dex0, dex1)
        (reserve_low, reserve_high) = (reserve0, reserve1)
        (path_low_inToken, path_low_outToken, path_low_middleToken) = (path0_inToken, path0_outToken, path0_middleToken)
        (path_high_inToken, path_high_outToken, path_high_middleToken) = (path1_inToken, path1_outToken, path1_middleToken)
    else:
        (dex_low, dex_high) = (dex1, dex0)
        (reserve_low, reserve_high) = (reserve1, reserve0)
        (path_low_inToken, path_low_outToken, path_low_middleToken) = (path1_inToken, path1_outToken, path1_middleToken)
        (path_high_inToken, path_high_outToken, path_high_middleToken) = (path0_inToken, path0_outToken, path0_middleToken)

    # Calculate gap
    gap = (reserve_high - reserve_low) / reserve_high
    logger.info(f"Gap: {gap*100:.2f}%")

    if gap <= 0:
        logger.warning(f"Gap {gap} <= 0, no arbitrage opportunity")
        return

    if gap <= min_gap:
        logger.warning(f"Gap {gap*100:.2f}% <= min_gap {min_gap*100:.2f}%")
        return

    # Calculate price impacts
    price_impact_high = price_impact_base(dex_high, amount, path_high_inToken, path_high_outToken, path_high_middleToken)
    amount_token = amount * dex_high.reserve_ratio(path_high_inToken, path_high_outToken, path_high_middleToken)
    price_impact_low = price_impact_token(dex_low, amount_token, path_low_inToken, path_low_outToken, path_low_middleToken)

    logger.info(f"Price impact high: {price_impact_high*100:.2f}%")
    logger.info(f"Price impact low: {price_impact_low*100:.2f}%")

    # Net profit calculation
    filter_gap = gap - abs(price_impact_low) - abs(price_impact_high)
    logger.info(f"Net gap after impacts: {filter_gap*100:.2f}%")

    if filter_gap <= min_gap:
        logger.warning(f"Net gap {filter_gap*100:.2f}% <= min_gap {min_gap*100:.2f}%, not executing")
        return

    # Check approvals
    dex_high_token = path_high_outToken if path_high_inToken is None or path_high_inToken == dex0.base_address else path_high_inToken
    if not dex_high.check_approval(wallet_address, dex_high_token):
        logger.info(f"Approving {dex_high_token} on {dex_high.platform}")
        tx = approve(dex_high, dex_high_token, wallet_address, private_key)
        logger.info(f"Approve tx: {tx['hash']}")

    dex_low_token = path_low_outToken if path_low_inToken is None or path_low_inToken == dex1.base_address else path_low_inToken
    if not dex_low.check_approval(wallet_address, dex_low_token):
        logger.info(f"Approving {dex_low_token} on {dex_low.platform}")
        tx = approve(dex_low, dex_low_token, wallet_address, private_key)
        logger.info(f"Approve tx: {tx['hash']}")

    # Check balance
    in_balance = dex0.balance(wallet_address, path0_inToken)
    out_balance = dex0.balance(wallet_address, path0_outToken)
    base_balance = dex0.balance(wallet_address, dex0.base_address)

    logger.info(f"Balance {path0_inToken}: {in_balance}")
    logger.info(f"Balance {path0_outToken}: {out_balance}")
    logger.info(f"Base balance: {base_balance}")

    if amount >= in_balance:
        logger.error(f"Insufficient balance: {amount} >= {in_balance}")
        return

    # Execute buy on higher price DEX (lower liquidity)
    logger.info(f"Buying on {dex_high.platform}: {amount} USDC -> token")
    tx_buy = buy(dex_high, dex_high_token, amount, path_high_middleToken, wallet_address, private_key)
    logger.info(f"Buy tx: {tx_buy.get('hash', 'N/A')}")

    # Execute sell on lower price DEX (higher liquidity)
    nonce = tx_buy.get("nonce", 0) + 1
    logger.info(f"Selling on {dex_low.platform}: {amount_token} token -> USDC")
    tx_sell = sell(dex_low, dex_low_token, amount_token, path_low_middleToken, wallet_address, private_key, nonce=nonce)
    logger.info(f"Sell tx: {tx_sell.get('hash', 'N/A')}")

    # Wait for confirmations
    buy_hash = tx_buy.get("hash", "")
    sell_hash = tx_sell.get("hash", "")

    if buy_hash and not dex_high.wait_transaction(buy_hash, timeout=300):
        logger.error(f"Buy transaction timeout: {buy_hash}")
        return

    if sell_hash and not dex_low.wait_transaction(sell_hash, timeout=300):
        logger.error(f"Sell transaction timeout: {sell_hash}")
        return

    # Calculate profit
    last_in_balance = dex0.balance(wallet_address, path_low_inToken)
    last_out_balance = dex0.balance(wallet_address, path_low_outToken)

    logger.info(f"Final {path_low_inToken} balance: {last_in_balance}")
    logger.info(f"Final {path_low_outToken} balance: {last_out_balance}")

    profit_in = last_in_balance - in_balance
    profit_out = last_out_balance - out_balance

    logger.info(f"Profit {path_low_inToken}: {profit_in}")
    logger.info(f"Profit {path_low_outToken}: {profit_out}")

    logger.info("=" * 50)
    logger.info("ARBITRAGE COMPLETED")
    logger.info(f"Buy DEX: {dex_high.platform}")
    logger.info(f"Sell DEX: {dex_low.platform}")
    logger.info(f"Buy TX: {buy_hash}")
    logger.info(f"Sell TX: {sell_hash}")
    logger.info(f"Profit: {profit_out:.4f} USDC")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(demo())
