# Sn0opyDr0p

Agent chasseur d'airdrops : lit les mails du **Grimoire du Mage** (Gmail), vérifie chaque opportunité sur le web avec Claude, note potentiel / effort / risque, et tient `TRACKER.md` à jour par compte.

Chaque matin (GitHub Actions), il revérifie les airdrops suivis, en ajoute de nouveaux et t'envoie un compte rendu par mail (`REPORT.md`) : ce qui presse, quoi faire aujourd'hui, ce qu'on laisse tomber.

Il pilote aussi un **wallet dédié** (`0x50F3347425617069E61a9A27Cbb8d645d19996f8`, Arbitrum + Base) : quand un airdrop suivi demande de l'activité on-chain, il fait lui-même le bridge ou le swap via LI.FI, sous plafonds, et le note dans le compte rendu. Les airdrops obtenus arrivent sur ce wallet.

## Setup

```bash
cp .env.example .env              # Gmail, clé Claude, RPC
cp accounts.example.json accounts.json
uv sync
```

Gmail : activer la 2FA, créer un [mot de passe d'application](https://myaccount.google.com/apppasswords), IMAP activé dans les réglages.

## Usage

```bash
uv run --env-file .env hunter.py hunt              # mails des 14 derniers jours + web
uv run --env-file .env hunter.py hunt --send       # idem + compte rendu par mail
uv run --env-file .env hunter.py hunt --no-mail    # recherche web seule
uv run hunter.py mark monad-testnet main fait
uv run hunter.py mark monad-testnet main réclamé --amount "1200 MON"
uv run --env-file .env hunter.py tx --chain base --account main --to 0x... --value 0.001 --airdrop foo
```

## Run quotidien

`.github/workflows/hunt.yml` tourne tous les jours à 6h UTC (et à la main via *Run workflow*), puis commit `TRACKER.md`, `REPORT.md` et `state.json`. Secrets du repo : `CLAUDE_CODE_OAUTH_TOKEN` (ton abonnement Claude, généré par `claude setup-token` : l'analyse passe par Claude Code, sans crédits API), `GMAIL_USER`, `GMAIL_APP_PASSWORD`, et `PK_AGENT` (clé privée du wallet dédié, **uniquement** celui-là).

Variables du repo (*Settings → Secrets and variables → Actions → Variables*) :

| Variable | Défaut | Rôle |
|---|---|---|
| `AGENT_EXECUTE` | absent | `true` = l'agent signe ; sinon il propose seulement. C'est l'interrupteur. |
| `MAX_TX_USD` | 25 | plafond par transaction |
| `MAX_DAY_USD` | 50 | plafond de dépense par jour |

## Garde-fous on-chain

Agent automatique (`hunt --execute`) :

- Claude choisit dans un menu fermé (bridge/swap depuis ETH, vers ETH ou USDC, Arbitrum ↔ Base) ; il n'écrit jamais de calldata. La transaction vient de l'API LI.FI.
- Avant de signer, le code vérifie : contrat = LI.FI Diamond, expéditeur **et** destinataire = wallet agent, montant exact, perte < 10 %, plafonds par tx et par jour, réserve de gas, airdrop suivi et actif. La tx est simulée (`estimate_gas`) avant envoi.
- `PK_AGENT` doit correspondre à l'adresse du wallet agent, sinon rien n'est signé.
- Perte maximale possible = le solde du wallet dédié. N'y mets que le budget de l'agent.
- Couper l'agent : passer `AGENT_EXECUTE` à `false`, ou supprimer le secret `PK_AGENT`.

Transactions manuelles (`tx`) :

- La clé privée reste dans `.env`, Claude ne la voit jamais : c'est toi qui lances `tx`.
- `tx` refuse tout contrat absent de `ALLOWED_CONTRACTS` et toute valeur au-dessus de `MAX_TX_ETH`, puis demande de retaper la fin de l'adresse.
- Utilise un wallet dédié à faible solde. Les mails et pages web peuvent être piégés (faux sites, drainers) : vérifie l'adresse sur le site officiel avant de l'ajouter à l'allowlist.
- Un wallet par personne : le multi-comptes (sybil) se fait détecter et exclure.

## Tests

```bash
uv run pytest -q
```
