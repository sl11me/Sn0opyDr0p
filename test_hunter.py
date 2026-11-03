import email

import hunter


def test_check_tx():
    allow = ["0xAbC0000000000000000000000000000000000001"]
    assert hunter.check_tx(allow[0].lower(), 0.001, allow, 0.01) is None
    assert "ALLOWED" in hunter.check_tx("0xdead", 0.001, allow, 0.01)
    assert "plafond" in hunter.check_tx(allow[0], 1, allow, 0.01)


def test_body_html():
    msg = email.message_from_string(
        'Content-Type: text/html\n\n<p>Farm <a href="https://x.io">ici</a></p><script>bad()</script>')
    body = hunter._body(msg)
    assert "https://x.io" in body and "bad" not in body


def test_merge_render(tmp_path, monkeypatch):
    monkeypatch.setattr(hunter, "TRACKER", tmp_path / "T.md")
    state = {"airdrops": {}, "progress": {}, "seen_emails": []}
    a = hunter.Airdrop(slug="foo", name="Foo", chain="Base", summary="s", potential=4, effort=2, risk=1,
                       cost_usd="~2$", deadline="inconnue", deadline_date="", next_action="bridge", alive=True,
                       who="agent", action_url="", how_to=[],
                       steps=["bridge"], links=["https://foo.xyz"], red_flags=[])
    assert hunter.merge(state, [a]) == ["foo"]
    assert hunter.merge(state, [a]) == []
    state["progress"]["foo"]["main"] = "fait"
    hunter.render(state)
    md = (tmp_path / "T.md").read_text()
    assert "[Foo](https://foo.xyz)" in md and "main: fait" in md and "★★★★" in md


def test_report():
    from datetime import date, timedelta
    soon = (date.today() + timedelta(days=3)).isoformat()
    far = (date.today() + timedelta(days=60)).isoformat()
    base = dict(name="X", potential=3, risk=2, next_action="claim", alive=True)
    state = {"airdrops": {"a": base | {"deadline_date": soon}, "b": base | {"deadline_date": far, "name": "Far"},
                          "dead": base | {"alive": False, "name": "Dead"}},
             "progress": {"a": {"main": "fait"}}}
    r = hunter.build_report(state, "Brief.", ["b"], 2)
    assert soon in r and far not in r and "Dead" not in r
    assert "main: fait" in r and "## 🆕 Nouveaux" in r


W = "0x50F3347425617069E61a9A27Cbb8d645d19996f8"


def _action(**kw):
    return hunter.Action(**({"airdrop": "a", "from_chain": "arbitrum", "to_chain": "base", "to_token": "ETH",
                             "amount_usd": 10, "reason": "r"} | kw))


def test_check_action():
    state = {"airdrops": {"a": {"alive": True}, "dead": {"alive": False}}}
    assert hunter.check_action(_action(), state, 0, 25, 50) is None
    assert "plafond par tx" in hunter.check_action(_action(amount_usd=30), state, 0, 25, 50)
    assert "plafond du jour" in hunter.check_action(_action(), state, 45, 25, 50)
    assert "même chaîne" in hunter.check_action(_action(to_chain="arbitrum"), state, 0, 25, 50)
    assert hunter.check_action(_action(to_chain="arbitrum", to_token="USDC"), state, 0, 25, 50) is None
    assert "clos" in hunter.check_action(_action(airdrop="dead"), state, 0, 25, 50)


def test_verify_quote():
    wei = 3 * 10**15
    q = {"transactionRequest": {"to": hunter.LIFI_DIAMOND.lower(), "chainId": 42161, "from": W, "value": hex(wei)},
         "action": {"fromAddress": W, "toAddress": W.lower(), "fromAmount": str(wei)},
         "estimate": {"fromAmountUSD": "6.9", "toAmountUSD": "6.87"}}
    assert hunter.verify_quote(q, 42161, W, wei, True, 25) is None
    assert "chaîne" in hunter.verify_quote(q, 8453, W, wei, True, 25)
    assert "montant" in hunter.verify_quote(q, 42161, W, wei + 1, True, 25)
    bad = {**q, "action": {**q["action"], "toAddress": "0x000000000000000000000000000000000000dEaD"}}
    assert "destinataire" in hunter.verify_quote(bad, 42161, W, wei, True, 25)
    bad = {**q, "transactionRequest": {**q["transactionRequest"], "to": "0x000000000000000000000000000000000000dEaD"}}
    assert "contrat" in hunter.verify_quote(bad, 42161, W, wei, True, 25)
    bad = {**q, "estimate": {"fromAmountUSD": "6.9", "toAmountUSD": "5"}}
    assert "perte" in hunter.verify_quote(bad, 42161, W, wei, True, 25)


def test_run_actions_without_key(monkeypatch):
    monkeypatch.delenv("PK_AGENT", raising=False)
    state = {"airdrops": {"a": {"alive": True}}, "progress": {}}
    hunter.run_actions(state, [_action(), _action(amount_usd=99)], execute=True)
    assert [e["status"] for e in state["executions"]] == ["proposée", "refusée : 99.0$ hors plafond par tx (25.0$)"]
    assert state["progress"] == {}


def test_html_mail():
    from datetime import date, timedelta
    soon = (date.today() + timedelta(days=2)).isoformat()
    base = dict(potential=3, risk=2, alive=True, links=["https://foo.xyz"], deadline_date="")
    state = {"airdrops": {
        "claim": base | {"name": "Claim <Foo>", "who": "toi", "deadline_date": soon, "next_action": "claimer",
                         "action_url": "https://claim.foo.xyz/app", "how_to": ["Connecte le wallet", "Signe **claim**"]},
        "evil": base | {"name": "Evil", "who": "toi", "next_action": "x", "action_url": "javascript:alert(1)",
                        "links": [], "how_to": []},
        "zzz": base | {"name": "Dodo", "who": "attendre", "next_action": "rien"}},
        "progress": {}, "executions": [{"date": str(date.today()), "airdrop": "claim", "chain": "base", "usd": 10,
                                        "desc": "arbitrum→base ETH→ETH", "reason": "r", "tx": "0xabc", "status": "envoyée"}]}
    wallet = {"address": "0x1", "balances": {"base": {"eth": 0.1, "usdc": 0, "usd": 230}}}
    h = hunter.build_html(state, "- 🔥 **Vite** [site](https://foo.xyz)", [], 1, wallet=wallet)
    assert "Claim &lt;Foo&gt;" in h and "<Foo>" not in h            # échappé
    assert 'href="https://claim.foo.xyz/app"' in h and "Ouvrir claim.foo.xyz" in h
    assert "javascript:" not in h                                    # lien non https ignoré
    assert "<b>claim</b>" in h and "<b>Vite</b>" in h and "demain" not in h and "dans 2 j" in h
    assert "https://basescan.org/tx/0xabc" in h and "✅" in h and "Dodo" in h
    md = hunter.build_report(state, "- ok", [], 1, wallet=wallet)
    assert md.index("À toi de jouer") < md.index("Le brief") and "1. Connecte le wallet" in md


def test_verify_quote_usdc():
    q = {"transactionRequest": {"to": hunter.LIFI_DIAMOND, "chainId": 8453, "from": W, "value": "0x0"},
         "action": {"fromAddress": W, "toAddress": W, "fromAmount": "5000000"},
         "estimate": {"fromAmountUSD": "5", "toAmountUSD": "4.99", "approvalAddress": hunter.LIFI_DIAMOND}}
    assert hunter.verify_quote(q, 8453, W, 5_000_000, False, 25) is None
    assert "montant" in hunter.verify_quote(q, 8453, W, 5_000_000, True, 25)   # natif attendu, value=0
    bad = {**q, "estimate": {**q["estimate"], "approvalAddress": "0x000000000000000000000000000000000000dEaD"}}
    assert "approbation" in hunter.verify_quote(bad, 8453, W, 5_000_000, False, 25)


def test_check_action_vaults():
    state = {"airdrops": {"a": {"alive": True}}}
    ok = _action(kind="deposit", vault="aave-usdc-base", airdrop="")
    assert hunter.check_action(ok, state, 0, 25, 50) is None
    assert "hors liste" in hunter.check_action(_action(kind="deposit", vault="evil"), state, 0, 25, 50)
    assert "plafond par tx" in hunter.check_action(_action(kind="deposit", vault="aave-usdc-base", amount_usd=40), state, 0, 25, 50)
    assert hunter.check_action(_action(kind="withdraw", vault="spark-usdc-base", amount_usd=0), state, 49, 25, 50) is None
    assert "même chaîne" in hunter.check_action(_action(to_chain="arbitrum", from_token="USDC", to_token="USDC"), state, 0, 25, 50)
    log = {"executions": [{"date": str(__import__("datetime").date.today()), "status": "envoyée", "usd": 20, "kind": "withdraw"},
                          {"date": str(__import__("datetime").date.today()), "status": "envoyée", "usd": 10}]}
    assert hunter.spent_today(log) == 10


def test_vault_calldata():
    from web3 import Web3
    w3 = Web3()
    me = "0x50F3347425617069E61a9A27Cbb8d645d19996f8"
    pool = hunter._c(w3, hunter.CHAINS["base"]["aave_pool"], hunter.AAVE_POOL)
    vault = hunter._c(w3, hunter.VAULTS["spark-usdc-base"]["token"], hunter.ERC4626)
    weth = hunter._c(w3, hunter.CHAINS["base"]["weth"], hunter.WETH)
    usdc = hunter.CHAINS["base"]["usdc"]
    assert pool.encode_abi("supply", args=[usdc, 1, me, 0])[:10] == "0x617ba037"
    assert pool.encode_abi("withdraw", args=[usdc, 1, me])[:10] == "0x69328dec"
    assert vault.encode_abi("deposit", args=[1, me])[:10] == "0x6e553f65"
    assert vault.encode_abi("redeem", args=[1, me, me])[:10] == "0xba087652"
    assert vault.encode_abi("withdraw", args=[1, me, me])[:10] == "0xb460af94"
    assert weth.encode_abi("deposit", args=[])[:10] == "0xd0e30db0"
    assert weth.encode_abi("withdraw", args=[1])[:10] == "0x2e1a7d4d"
    assert vault.encode_abi("approve", args=[me, 5])[:10] == "0x095ea7b3"


def test_pick_validator():
    v = lambda name, stake, **kw: {"name": name, "validator": name, "stake": stake, "isActive": True, "isJailed": False,
                                   "commission": "0.03", "stats": [["day", {"uptimeFraction": "1.0"}]]} | kw
    vals = [v("gros-jaile", 900, isJailed=True), v("cher", 800, commission="0.2"), v("instable", 700,
            stats=[["day", {"uptimeFraction": "0.9"}]]), v("inactif", 600, isActive=False), v("bon", 500), v("petit", 100)]
    assert hunter.pick_validator(vals)["name"] == "bon"


def test_check_action_hype():
    state = {"airdrops": {"hyperliquid-s2": {"alive": True}}}
    assert hunter.check_action(_action(kind="hype_stake", airdrop="hyperliquid-s2", amount_usd=20), state, 0, 25, 50) is None
    assert hunter.check_action(_action(kind="hype_stake", airdrop="", amount_usd=0), state, 50, 25, 50) is None  # restake
    assert "plafond par tx" in hunter.check_action(_action(kind="hype_stake", airdrop="", amount_usd=30), state, 0, 25, 50)
    assert hunter.describe(_action(kind="hype_stake", amount_usd=0)).startswith("staking HYPE")
