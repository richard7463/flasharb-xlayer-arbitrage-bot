#!/usr/bin/env python3
"""
DexFight - X Layer Edition
Forked from dexfight, adapted for X Layer

Supported DEXes on X Layer:
- Uniswap V3
- Sushiswap
- Pancakeswap
- OKX DEX
"""

# X Layer Chain Configuration
CHAIN = {
    "name": "X Layer",
    "chain_id": 196,  # X Layer mainnet
    "rpc_url": "https://rpc.xlayer.com",
    "explorer": "https://www.okx.com/explorer/xlayer",
}

# Native token
NATIVE_TOKEN = "XLM"  # X Layer's native token (actually ETH on EVM)

# Base token (USDC)
BASE_TOKEN = {
    "symbol": "USDC",
    "address": "0x74b6b8cd8021f6855b14e0e0c3d47d72c5e8b7bb",
    "decimals": 6,
}

# DEX Factory and Router addresses on X Layer
DEX_CONFIGS = {
    "uniswap_v3": {
        "name": "Uniswap V3",
        "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "router": "0xE592427A0AEce92De3Edee1F18E0157C05881564",
        "pool_init_code_hash": "0xe34f199b19b2b4f47f68442619bb96d1bb3ee964",
    },
    "sushiswap": {
        "name": "Sushiswap",
        "factory": "0xC0AEe478e3658e261099c5B1Cd55C7F1c552e817",
        "router": "0xd9e1ce17f2641f24be83665cba2da6c6cb6f7e83",
    },
    "pancakeswap": {
        "name": "Pancakeswap",
        "factory": "0x0eD7e52944161450477ee417DE9Cd3a749b7dd35",
        "router": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
    },
    "okx": {
        "name": "OKX DEX",
        "factory": "0x0eD7e52944161450477ee417DE9Cd3a749b7dd35",
        "router": "0xb94f689f214ade8d3e83136d3ade815f542a9b3b",
    },
}

# Token addresses on X Layer (example tokens)
TOKENS = {
    "USDC": {
        "address": "0x74b6b8cd8021f6855b14e0e0c3d47d72c5e8b7bb",
        "decimals": 6,
    },
    "USDT": {
        "address": "0x5DE1678304E92F6D7552a4A9f2A5E0e7E9fE6c9a",
        "decimals": 6,
    },
    "WIF": {
        "address": "0x1C9A2D6b4c5E6f7890a1b2c3d4e5f6a7b8c9d0e1",
        "decimals": 6,
    },
    "PEPE": {
        "address": "0x2A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B",
        "decimals": 18,
    },
    "SHIB": {
        "address": "0x3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D8E9F0A1B2",
        "decimals": 18,
    },
    "GIGA": {
        "address": "0x4C5D6E7F8A9B0C1D2E3F4A5B6C7D8E9F0A1B2C3",
        "decimals": 6,
    },
    "NEIRO": {
        "address": "0x5D6E7F8A9B0C1D2E3F4A5B6C7D8E9F0A1B2C3D4",
        "decimals": 9,
    },
}

# Minimum configuration
MIN_GAP = 0.01  # 1% minimum spread
MIN_LIQUIDITY = 10000  # Minimum liquidity to consider
CHECK_INTERVAL = 30  # Seconds between checks

print("DexFight X Layer Edition loaded")
print(f"Chain: {CHAIN['name']} (ID: {CHAIN['chain_id']})")
print(f"RPC: {CHAIN['rpc_url']}")
print(f"Supported DEXes: {', '.join(DEX_CONFIGS.keys())}")
