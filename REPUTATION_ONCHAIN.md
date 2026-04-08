# Agent Reputation Protocol - 上链方案

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户界面                              │
│  - Agent 列表  - 信誉查询  - 排名榜                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      索引服务 (Indexer)                       │
│  - 监听 X Layer 链上交易                                     │
│  - 解析 Agent 交易数据                                       │
│  - 计算信誉分                                                 │
│  - 更新合约                                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    X Layer 链上 (Chain 196)                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           ReputationRegistry.sol                      │  │
│  │                                                      │  │
│  │  mapping(address => AgentReputation) public agents;   │  │
│  │                                                      │  │
│  │  - totalTx                                            │  │
│  │  - successCount                                       │  │
│  │  - totalGas                                           │  │
│  │  - totalProfit                                        │  │
│  │  - score (0-100)                                       │  │
│  │  - tier (C/CC/CCC/BBB/AAA)                            │  │
│  │  - lastUpdate                                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 上链方式

### 方式 A: 自动同步 (推荐)

```
链上交易发生 → 索引器监听 → 解析数据 → 链上更新信誉
```

**流程**:
1. 索引器监听 X Layer 所有 Agent 交易
2. 解析交易类型、金额、成功/失败
3. 调用合约 `recordTransaction()` 更新
4. 链上数据始终最新

**优点**: 全自动，数据真实

---

### 方式 B: 手动上报

```
Agent 交易后 → 调用我们的 API → 链上更新信誉
```

**流程**:
1. Agent 完成交易后，调用我们 API
2. API 验证交易真实性 (OKLink 查询)
3. 调用合约 `recordTransaction()`
4. 更新信誉

**优点**: 简单，不依赖索引器

**缺点**: 需要 Agent 主动配合

---

## 智能合约设计

### ReputationRegistry.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract ReputationRegistry {

    // Agent 信誉结构
    struct AgentReputation {
        uint256 totalTx;        // 总交易数
        uint256 successCount;   // 成功数
        uint256 failureCount;   // 失败数
        uint256 totalGas;       // 总 Gas
        int256 totalProfit;     // 总盈利 (可正可负)
        uint256 score;          // 信誉分 0-100
        uint8 tier;             // 等级: 1=C, 2=CC, 3=CCC, 4=BBB, 5=BB, 6=B, 7=A, 8=AA, 9=AAA
        uint256 lastUpdate;     // 上次更新时间
    }

    // 地址 → 信誉
    mapping(address => AgentReputation) public agents;

    // 事件
    event TransactionRecorded(
        address indexed agent,
        bool success,
        uint256 gasUsed,
        int256 profit,
        uint256 newScore,
        uint8 newTier
    );

    event ReputationQueried(
        address indexed agent,
        uint256 score,
        uint8 tier
    );

    // 记录交易 (任何人可调用)
    function recordTransaction(
        address agent,
        bool success,
        uint256 gasUsed,
        int256 profit
    ) external {
        AgentReputation storage rep = agents[agent];

        // 更新数据
        rep.totalTx++;
        if (success) {
            rep.successCount++;
            rep.totalProfit += profit;
        } else {
            rep.failureCount++;
            rep.totalProfit += profit; // profit 可以是负数
        }
        rep.totalGas += gasUsed;
        rep.lastUpdate = block.timestamp;

        // 计算新分数
        (rep.score, rep.tier) = _calculateScore(rep);

        emit TransactionRecorded(agent, success, gasUsed, profit, rep.score, rep.tier);
    }

    // 查询信誉 (view 函数，不消耗 gas)
    function getReputation(address agent) external view returns (
        uint256 score,
        uint8 tier,
        uint256 totalTx,
        uint256 successRate,
        int256 totalProfit,
        uint256 avgGas
    ) {
        AgentReputation storage rep = agents[agent];

        uint256 successRate = rep.totalTx > 0
            ? (rep.successCount * 10000) / rep.totalTx // 万分比
            : 0;

        uint256 avgGas = rep.totalTx > 0
            ? rep.totalGas / rep.totalTx
            : 0;

        return (
            rep.score,
            rep.tier,
            rep.totalTx,
            successRate,
            rep.totalProfit,
            avgGas
        );
    }

    // 计算分数算法
    function _calculateScore(AgentReputation storage rep) internal view returns (uint256, uint8) {
        if (rep.totalTx == 0) return (0, 0);

        // 1. 交易次数得分 (上限 20)
        uint256 txScore = rep.totalTx >= 200 ? 20 : rep.totalTx / 10;

        // 2. 成功率得分 (上限 30)
        uint256 successRate = (rep.successCount * 100) / rep.totalTx;
        uint256 successScore = (successRate * 30) / 100;

        // 3. 盈利得分 (上限 30)
        uint256 profitScore = 0;
        if (rep.totalProfit > 0) {
            if (rep.totalProfit >= 10000 ether) profitScore = 30;
            else if (rep.totalProfit >= 1000 ether) profitScore = 20;
            else if (rep.totalProfit >= 100 ether) profitScore = 10;
            else profitScore = 5;
        }

        // 4. Gas 效率得分 (上限 20)
        uint256 avgGas = rep.totalGas / rep.totalTx;
        uint256 gasScore = avgGas <= 0.001 ether ? 20 : 10;

        // 总分
        uint256 totalScore = txScore + successScore + profitScore + gasScore;
        totalScore = totalScore > 100 ? 100 : totalScore;

        // 等级
        uint8 tier = _scoreToTier(totalScore);

        return (totalScore, tier);
    }

    function _scoreToTier(uint256 score) internal pure returns (uint8) {
        if (score >= 90) return 9;  // AAA
        if (score >= 80) return 8;  // AA
        if (score >= 70) return 7;  // A
        if (score >= 60) return 6;  // BBB
        if (score >= 50) return 5;  // BB
        if (score >= 40) return 4;  // B
        if (score >= 30) return 3;  // CCC
        if (score >= 20) return 2;  // CC
        return 1; // C
    }
}
```

---

## 索引器实现

### Python (使用 OKLink API)

```python
from web3 import Web3
import requests

# X Layer RPC
RPC_URL = "https://xlayer-rpc.com"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# OKLink API 获取交易
def get_agent_transfers(address: str, start_block: int):
    url = f"https://www.oklink.com/api/v5/explorer/address/transaction-list"
    params = {
        "chainShortName": "xlayer",
        "address": address,
        "startBlock": start_block
    }
    headers = {"Ok-Access-Key": API_KEY}
    return requests.get(url, params=params, headers=headers).json()

# 监听新交易
def sync_reputation():
    latest_block = w3.eth.block_number

    # 遍历所有已知 Agent 地址
    for agent in known_agents:
        txs = get_agent_transfers(agent, last_synced_block)

        for tx in txs:
            # 解析交易
            success = tx.get("status") == "1"
            gas_used = int(tx.get("gasUsed", 0))
            # 计算 profit 需要解析 internal transfers

            # 更新链上信誉
            contract.functions.recordTransaction(
                agent,
                success,
                gas_used,
                profit  # 需要计算
            ).transact({"from": admin_wallet})
```

---

## 前端交互

### Next.js + wagmi

```tsx
import { useContractRead } from 'wagmi'
import { ReputationABI } from '@/abi/ReputationRegistry'

// 查询信誉
const { data } = useContractRead({
  address: CONTRACT_ADDRESS,
  abi: ReputationABI,
  functionName: 'getReputation',
  args: [agentAddress],
})

// 显示
<div>
  <p>Score: {data?.score}</p>
  <p>Tier: {data?.tier === 9 ? 'AAA' : 'AA'}</p>
  <p>Total Tx: {data?.totalTx}</p>
  <p>Success Rate: {data?.successRate / 100}%</p>
</div>
```

---

## 部署信息

```
网络: X Layer (Chain ID: 196)
合约: ReputationRegistry.sol
地址: 0x0000000000000000000000000000000000000001 (示例)

Gas 估算:
- recordTransaction: ~50,000 gas
- getReputation: ~30,000 gas (view)
```

---

## 数据流总结

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Agent 交易  │ ──▶ │  索引器     │ ──▶ │  链上合约   │
│ (X Layer)   │     │ (OKLink API)│     │  更新信誉   │
└─────────────┘     └─────────────┘     └─────────────┘
                                                 │
                                                 ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  前端展示   │ ◀── │  查询 API   │ ◀── │  链上存储   │
│  (score/tier)│     │ (getReputation)│   │ (合约读取) │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## 总结

| 步骤 | 操作 |
|------|------|
| 1 | 索引器监听 X Layer 链上交易 |
| 2 | 解析交易数据 (成功/失败/盈利/Gas) |
| 3 | 调用合约 `recordTransaction()` |
| 4 | 链上计算分数和等级 |
| 5 | 前端通过 `getReputation()` 读取 |

**关键**: 数据来自链上，无法伪造