# Agent Transaction Reputation Protocol
## "AI Agent 的链上交易信用分"

---

## 核心理念

**只关注链上交易行为，不看身份**

- 任何 Agent 的交易历史都是公开的
- 交易频率、成功率、盈亏、Gas 费用
- 这些数据无法伪造，最可信

---

## 和现有项目的区别

| 项目 | 关注点 | 我们 |
|------|--------|------|
| Attestix | 合规 + EU AI Act | 专注交易 |
| AgenticID | 身份验证 | 专注行为 |
| 普通项目 | 静态身份 | **动态交易记录** |

---

## 产品功能

### 1. 交易记录 (Transaction History)

```
记录每个 Agent 在 X Layer 上的:
- 交易次数
- 成功/失败率
- 平均 Gas 费用
- 交易类型 (swap / defi / bridge)
- 时间分布
```

**数据来源**: X Layer 公开链数据 (OKLink API)

---

### 2. 信誉评分 (Reputation Score)

```
Score = f(交易次数, 成功率, 盈利, Gas效率, 时间衰减)

公式:
Score = (交易次数 * 0.1) + (成功率 * 30) + (盈利 * 0.5) + (Gas效率 * 20) - (时间衰减)

范围: 0-100 分
- 90+ 极好
- 70-89 优秀
- 50-69 一般
- <50 差
```

---

### 3. 信誉查询 API

```python
# 查询 Agent 信誉
GET /api/reputation?address=0x...

Response:
{
  "address": "0x...",
  "score": 85,
  "totalTx": 1234,
  "successRate": 0.98,
  "totalProfit": 150.5,
  "avgGas": 0.001,
  "rank": 15,
  "tier": "AAA"
}
```

---

### 4. 信誉应用场景

| 场景 | 用处 |
|------|------|
| DeFi 借贷 | 高信誉 = 高额度 / 低抵押率 |
| 跨链桥 | 高信誉 = 高额度 / 低手续费 |
| 交易所 | 高信誉 = 优先处理 |
| A2A 市场 | 高信誉 = 接更多单 |
| 保险 | 高信誉 = 低保费 |

---

## 链上实现

### 智能合约: ReputationRegistry.sol

```solidity
contract ReputationRegistry {
    struct AgentReputation {
        uint256 totalTx;
        uint256 successCount;
        uint256 totalGas;
        int256 totalProfit;
        uint256 lastUpdate;
        uint8 tier; // 1=C, 2=CC, 3=CCC, 4=BBBB, 5=AAA
    }

    mapping(address => AgentReputation) public reputations;

    // 每次交易后更新
    function recordTransaction(
        address agent,
        bool success,
        uint256 gasUsed,
        int256 profit
    ) external {
        AgentReputation storage rep = reputations[agent];

        rep.totalTx++;
        if (success) rep.successCount++;
        rep.totalGas += gasUsed;
        rep.totalProfit += profit;
        rep.lastUpdate = block.timestamp;

        // 计算 tier
        rep.tier = _calculateTier(rep);

        emit ReputationUpdated(agent, rep.tier, _calculateScore(rep));
    }

    function getReputation(address agent) external view returns (
        uint256 score,
        uint8 tier,
        uint256 totalTx,
        uint256 successRate
    );
}
```

---

## 数据来源

### OKX Skills / API

| 数据 | 来源 |
|------|------|
| 交易历史 | `okx-wallet-portfolio` |
| Gas 费用 | `okx-onchain-gateway` |
| Token 价格 | `okx-dex-market` |
| 盈亏计算 | `okx-defi-portfolio` |

---

## 计分算法细节

```python
def calculate_score(rep: AgentReputation) -> int:
    # 1. 交易次数得分 (上限 20)
    tx_score = min(rep.total_tx / 10, 20)

    # 2. 成功率得分 (上限 30)
    success_rate = rep.success_count / rep.total_tx
    success_score = success_rate * 30

    # 3. 盈利得分 (上限 30)
    if rep.total_profit > 0:
        profit_score = min(rep.total_profit / 10, 30)
    else:
        profit_score = 0

    # 4. Gas 效率 (上限 20)
    avg_gas = rep.total_gas / rep.total_tx
    gas_score = max(0, 20 - avg_gas * 1000)

    # 5. 时间衰减 (6个月后开始衰减)
    days_since = (now - rep.last_update) / 86400
    decay = max(0, 1 - days_since / 180)

    total = (tx_score + success_score + profit_score + gas_score) * decay
    return int(min(total, 100))
```

---

## 展示界面

```
┌─────────────────────────────────────────────────┐
│           Agent Reputation Dashboard            │
├─────────────────────────────────────────────────┤
│                                                 │
│   0xbcd403e543529cb9e6a90fd736f4477bcd9ad8c8   │
│                                                 │
│   Score: 85 ─────────────────────── ████████░   │
│   Tier: AAA                                     │
│                                                 │
│   ┌─────────────┬─────────────┐               │
│   │ 总交易: 1234 │ 成功率: 98% │               │
│   │ 总盈利: $150│ 平均Gas: 0.001│              │
│   └─────────────┴─────────────┘               │
│                                                 │
│   排名: #15 / 1,000 Agents                     │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 商业模式

| 模式 | 说明 |
|------|------|
| 免费 API | 基础查询 (信誉分 + 排名) |
| 高级 API | 历史分析 + 趋势预测 |
| 认证服务 | 给 Agent 认证 (类似芝麻信用) |
| 嵌入费 | DeFi 协议集成收费 |

---

## 零重叠确认

**之前的项目没有专注链上交易行为评分**

- Attestix: 合规
- AgenticID: 身份
- 其他 DeFi: 套利/借贷

**我们**: 专注交易数据 → 信誉评分 → 应用场景

---

## 总结

| 维度 | 说明 |
|------|------|
| 做什么 | 记录 X Layer 上所有 Agent 的交易行为 |
| 怎么评 | 交易次数 + 成功率 + 盈利 + Gas 效率 |
| 有什么用 | 借贷额度 / 桥接限额 / 接单优先级 |
| 优势 | 数据公开无法伪造 + 场景明确 |