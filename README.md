# Sn0opyDr0p

Agent chasseur d'airdrops : lit les mails du **Grimoire du Mage** (Gmail), vérifie chaque opportunité sur le web avec Claude, note potentiel / effort / risque, et tient `TRACKER.md` à jour par compte.

Chaque matin (GitHub Actions), il revérifie les airdrops suivis, en ajoute de nouveaux et t'envoie un compte rendu par mail (`REPORT.md`) : ce qui presse, quoi faire aujourd'hui, ce qu'on laisse tomber.

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

`.github/workflows/hunt.yml` tourne tous les jours à 6h UTC (et à la main via *Run workflow*), puis commit `TRACKER.md`, `REPORT.md` et `state.json`. Secrets du repo à créer : `ANTHROPIC_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`. Aucune clé privée de wallet ne va sur GitHub : les transactions restent locales.

## Garde-fous on-chain

- La clé privée reste dans `.env`, Claude ne la voit jamais et ne déclenche aucune transaction : c'est toi qui lances `tx`.
- `tx` refuse tout contrat absent de `ALLOWED_CONTRACTS` et toute valeur au-dessus de `MAX_TX_ETH`, puis demande de retaper la fin de l'adresse.
- Utilise un wallet dédié à faible solde. Les mails et pages web peuvent être piégés (faux sites, drainers) : vérifie l'adresse sur le site officiel avant de l'ajouter à l'allowlist.
- Un wallet par personne : le multi-comptes (sybil) se fait détecter et exclure.

## Tests

```bash
uv run pytest -q
```
