# AI Content Rights Market - 完整上链方案

## 最终产品架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户界面 (Web/App)                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ 上传    │  │ 市场    │  │ 购买    │  │ 钱包    │        │
│  │ 作品    │  │ 浏览    │  │ 授权    │  │ 连接    │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
└───────┼────────────┼────────────┼────────────┼─────────────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI Content API (后端)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 内容处理     │  │ 版权验证     │  │ 交易处理     │      │
│  │ (存IPFS)    │  │ (哈希计算)   │  │ (x402)       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    X Layer 链上 (Chain 196)                 │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           ContentRegistry.sol                       │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │   │
│  │  │ 注册   │  │ 授权   │  │ 分成   │  │ 查询   │  │   │
│  │  │ register│  │ license│  │ claim  │  │ getInfo│  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           ContentNFT.sol (ERC-721)                   │   │
│  │  - tokenId → 内容哈希                                 │   │
│  │  - metadata → 版权信息                                │   │
│  │  - royalty => 创作者分成                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 上链流程 (Step by Step)

### 1. 内容注册 (Register)

```
用户上传 AI 生成的内容 (图片/代码/文章)
        │
        ▼
后端计算内容哈希 (SHA-256)
        │
        ▼
内容上传到 IPFS (去中心化存储)
        │
        ▼
调用合约: ContentRegistry.registerContent()
        │
        ├── 参数: contentHash, metadata, creator
        │
        ├── 链上记录:
        │   - contentId (自增)
        │   - contentHash (哈希)
        │   - ipfsHash (存储位置)
        │   - creator (创作者地址)
        │   - timestamp (注册时间)
        │   - royaltyPercent (分成比例)
        │
        └── 返回: contentId + tx hash
```

**合约代码**:
```solidity
function registerContent(
    bytes32 contentHash,
    string memory ipfsHash,
    string memory metadata,
    uint256 royaltyPercent
) external returns (uint256) {
    require(royaltyPercent <= 100, "Royalty too high");

    uint256 contentId = nextContentId++;
    contents[contentId] = Content({
        contentHash: contentHash,
        ipfsHash: ipfsHash,
        creator: msg.sender,
        timestamp: block.timestamp,
        royaltyPercent: royaltyPercent,
        totalEarnings: 0
    });

    emit ContentRegistered(contentId, msg.sender, contentHash);
    return contentId;
}
```

---

### 2. 授权购买 (License)

```
用户 ( licensee ) 想使用内容
        │
        ▼
选择授权类型: view / commercial / exclusive
        │
        ▼
支付 USDC (通过 x402 或直接转账)
        │
        ▼
调用合约: ContentRegistry.licenseContent()
        │
        ├── 参数: contentId, licensee, licenseType, price
        │
        ├── 链上记录:
        │   - licenseId
        │   - contentId
        │   - licensee
        │   - licenseType
        │   - price
        │   - expiration
        │
        └── 返回: licenseId + tx hash
```

**合约代码**:
```solidity
function licenseContent(
    uint256 contentId,
    address licensee,
    uint8 licenseType, // 1=view, 2=commercial, 3=exclusive
    uint256 price
) external returns (uint256) {
    Content storage content = contents[contentId];
    require(content.creator != address(0), "Content not exist");

    // 计算分成
    uint256 royaltyAmount = (price * content.royaltyPercent) / 100;
    uint256 creatorAmount = price - royaltyAmount;

    // 转账
    content.creator.transfer(creatorAmount); // 创作者
    // royaltyAmount 进入分成池

    emit ContentLicensed(contentId, licensee, price);
    return licenseId;
}
```

---

### 3. 收益分成 (Royalty Distribution)

```
每次交易触发分成逻辑
        │
        ├── 创作者: 70%
        ├── 训练数据贡献者: 20%
        └── 平台: 10%
        │
        ▼
链上自动执行
        │
        ▼
记录: 内容总收入 += price
      各个地址收入 += 分成
```

---

## 智能合约结构

### ContentRegistry.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract ContentRegistry {
    struct Content {
        bytes32 contentHash;
        string ipfsHash;
        address creator;
        uint256 timestamp;
        uint256 royaltyPercent;
        uint256 totalEarnings;
    }

    struct License {
        address licensee;
        uint8 licenseType;
        uint256 price;
        uint256 expiration;
        bool active;
    }

    uint256 public nextContentId;
    mapping(uint256 => Content) public contents;
    mapping(uint256 => License[]) public licenses;

    event ContentRegistered(uint256 indexed contentId, address creator, bytes32 hash);
    event ContentLicensed(uint256 indexed contentId, address licensee, uint256 price);
    event RoyaltyPaid(uint256 indexed contentId, address recipient, uint256 amount);

    function registerContent(bytes32 contentHash, string memory ipfsHash, uint256 royaltyPercent)
        external returns (uint256);

    function licenseContent(uint256 contentId, uint8 licenseType)
        external payable returns (uint256);

    function getContent(uint256 contentId) external view returns (Content memory);

    function getLicenses(uint256 contentId) external view returns (License[] memory);
}
```

---

## 前端交互

### React/Next.js 示例

```tsx
import { useContractRead, useContractWrite } from 'wagmi'

// 1. 注册内容
const { write: register } = useContractWrite({
  address: CONTRACT_ADDRESS,
  abi: ContentRegistryABI,
  functionName: 'registerContent',
})

// 用户上传内容
const handleUpload = async (file) => {
  // 计算哈希
  const hash = await calculateHash(file)
  // 上传 IPFS
  const ipfsHash = await uploadToIPFS(file)
  // 调用合约
  await register({
    args: [hash, ipfsHash, 500] // 50% 版税
  })
}

// 2. 购买授权
const { write: license } = useContractWrite({
  address: CONTRACT_ADDRESS,
  abi: ContentRegistryABI,
  functionName: 'licenseContent',
})

const handleBuy = async (contentId, licenseType) => {
  await license({
    args: [contentId, licenseType],
    value: parseEther('0.01') // 0.01 USDC
  })
}
```

---

## OKX Skills 集成

| Skill | 用途 |
|-------|------|
| `okx-agentic-wallet` | 用户钱包连接、签名 |
| `okx-x402-payment` | 微支付 (授权费用) |
| `okx-dex-swap` | 如需兑换 USDC 支付 |
| `okx-wallet-portfolio` | 查看用户余额 |
| `okx-audit-log` | 版权交易记录审计 |
| `okx-onchain-gateway` | 交易 gas 估算 |

---

## 数据流总结

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  用户上传   │ -> │  计算哈希   │ -> │  存 IPFS    │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
                                              ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 链上查询    │ <- │  授权购买   │ <- │ 调用合约    │
└─────────────┘    └─────────────┘    └─────────────┘
       │                                     │
       ▼                                     ▼
┌─────────────┐                       ┌─────────────┐
│ 前端展示    │                       │ X Layer 链上 │
│ (市场/我的) │                       │ (交易记录)   │
└─────────────┘                       └─────────────┘
```

---

## 部署地址 (X Layer)

```
ContentRegistry: 0x0000000000000000000000000000000000000000 (待部署)
USDC: 0x74b7f16337b8972027f6196a17a631ac6de26d22 (X Layer 已有)
```

---

## 总结

| 步骤 | 链上操作 | 链下操作 |
|------|----------|----------|
| 注册 | ContentRegistry.registerContent() | 计算哈希、上传 IPFS |
| 授权 | ContentRegistry.licenseContent() | 展示内容详情 |
| 分成 | 合约内自动转账 | 通知用户 |
| 查询 | 读取合约状态 | 前端展示 |