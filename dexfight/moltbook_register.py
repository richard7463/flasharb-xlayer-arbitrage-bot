#!/usr/bin/env python3
"""
MOLTBOOK Agent 注册工具
========================
作用:
1) 按 skill.md 流程尝试注册 agent
2) 自动提取 claim link / verification code
3) 输出给 human 的 X 验证文案

用法:
python moltbook_register.py --name FlashArb --owner-x your_x_handle
"""

from __future__ import annotations

import argparse
import json
import os
import textwrap
from typing import Any, Dict, Iterable, Optional, Tuple

import requests


DEFAULT_BASE_URL = os.getenv("MOLTBOOK_BASE_URL", "https://www.moltbook.com").rstrip("/")
REQUEST_TIMEOUT = int(os.getenv("MOLTBOOK_TIMEOUT", "20"))


def _find_first_string(data: Dict[str, Any], keys: Iterable[str]) -> Optional[str]:
    keyset = {k.lower() for k in keys}

    def scan(node: Any) -> Optional[str]:
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() in keyset and isinstance(v, str) and v.strip():
                    return v.strip()
            for v in node.values():
                hit = scan(v)
                if hit:
                    return hit
        elif isinstance(node, list):
            for item in node:
                hit = scan(item)
                if hit:
                    return hit
        return None

    return scan(data)


def _extract_claim_info(resp_json: Dict[str, Any], base_url: str) -> Dict[str, str]:
    claim = _find_first_string(
        resp_json,
        [
            "claim_link",
            "claimLink",
            "claim_url",
            "claimUrl",
            "verification_link",
            "verificationLink",
            "verify_link",
            "verifyLink",
        ],
    )

    verification_code = _find_first_string(
        resp_json,
        [
            "verification_code",
            "verificationCode",
            "verify_code",
            "verifyCode",
            "challenge_code",
            "challengeCode",
            "code",
            "token",
        ],
    )

    agent_id = _find_first_string(resp_json, ["agent_id", "agentId", "id", "slug", "handle"])
    api_key = _find_first_string(resp_json, ["api_key", "apiKey", "key"])

    if claim and claim.startswith("/"):
        claim = f"{base_url}{claim}"

    # 如果 API 没直接给 claim link，尝试根据 token/code 构造常见路径
    if not claim and verification_code:
        claim = f"{base_url}/claim/{verification_code}"

    # 最后兜底: 给出 agent 主页，至少能继续手动 claim
    if not claim and agent_id:
        claim = f"{base_url}/agent/{agent_id}"

    result: Dict[str, str] = {}
    if claim:
        result["claim_link"] = claim
    if verification_code:
        result["verification_code"] = verification_code
    if agent_id:
        result["agent_id"] = agent_id
    if api_key:
        result["api_key"] = api_key

    return result


def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    except Exception as exc:
        return None, f"request failed: {exc}", -1

    status = resp.status_code
    if "application/json" in resp.headers.get("content-type", ""):
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:1000]}
    else:
        body = {"raw": resp.text[:1000]}

    if 200 <= status < 300:
        if isinstance(body, dict):
            return body, None, status
        return {"data": body}, None, status

    return None, f"HTTP {status}: {json.dumps(body, ensure_ascii=False)}", status


def register_agent(
    base_url: str,
    name: str,
    description: str,
    dry_run: bool,
) -> Dict[str, Any]:
    payload = {
        "name": name,
        "description": description,
    }

    # 兼容不同部署的路由
    endpoint_candidates = [
        f"{base_url}/api/v1/agents/register",
        f"{base_url}/api/v1/agent/register",
        f"{base_url}/api/agents/register",
        f"{base_url}/api/agent/register",
        f"{base_url}/api/agents",
        f"{base_url}/api/agent",
    ]

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "flasharb-moltbook-register/1.0",
    }

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "payload": payload,
            "endpoint_candidates": endpoint_candidates,
        }

    last_error = "unknown error"
    for endpoint in endpoint_candidates:
        body, err, status = _post_json(endpoint, payload, headers)
        if body is not None:
            parsed = _extract_claim_info(body, base_url)
            return {
                "ok": True,
                "endpoint": endpoint,
                "status": status,
                "response": body,
                "claim": parsed,
            }
        last_error = f"{endpoint}: {err}"

    return {
        "ok": False,
        "error": last_error,
        "payload": payload,
        "endpoint_candidates": endpoint_candidates,
    }


def _tweet_template(owner_x: str, claim_link: str, verification_code: str) -> str:
    if owner_x:
        handle = owner_x if owner_x.startswith("@") else f"@{owner_x}"
    else:
        handle = "<your_x_handle>"
    code_line = f"verification code: {verification_code}" if verification_code else "verification code: <from claim page>"
    return textwrap.dedent(
        f"""
        Verifying ownership of my Moltbook AI agent.
        owner: {handle}
        {code_line}
        claim: {claim_link}
        """
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Register Moltbook agent and get claim link")
    parser.add_argument("--name", default=os.getenv("MOLTBOOK_AGENT_NAME", "FlashArb"))
    parser.add_argument("--owner-x", default=os.getenv("MOLTBOOK_OWNER_X", ""))
    parser.add_argument("--description", default=os.getenv("MOLTBOOK_AGENT_DESC", "X Layer arbitrage agent powered by DexFight"))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = register_agent(
        base_url=args.base_url,
        name=args.name,
        description=args.description,
        dry_run=args.dry_run,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("dry_run"):
        print("\n[DRY-RUN] 未发起真实注册请求。")
        return 0

    if not result.get("ok"):
        return 1

    claim = result.get("claim", {})
    claim_link = claim.get("claim_link", "")
    verification_code = claim.get("verification_code", "")
    api_key = claim.get("api_key", "")

    if claim_link:
        print("\n=== CLAIM LINK ===")
        print(claim_link)
    else:
        print("\n[WARN] 注册成功，但响应里没有可识别 claim link。")
        print("请打开上面的 response 原文，查找 claim/verify 字段。")

    print("\n=== X VERIFY TWEET TEMPLATE ===")
    print(_tweet_template(args.owner_x, claim_link or "<paste-claim-link>", verification_code))

    if api_key:
        print("\n=== API KEY (SAVE NOW) ===")
        print(api_key)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
