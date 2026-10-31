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
                       cost_usd="~2$", deadline="inconnue", steps=["bridge"], links=["https://foo.xyz"], red_flags=[])
    hunter.merge(state, [a])
    state["progress"]["foo"]["main"] = "fait"
    hunter.render(state)
    md = (tmp_path / "T.md").read_text()
    assert "[Foo](https://foo.xyz)" in md and "main: fait" in md and "★★★★" in md
