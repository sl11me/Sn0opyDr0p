# Sn0opyDr0p

**Chirac**, l'agent chasseur d'airdrops : lit les newsletters de chasseurs d'airdrops (**Grimoire du Mage**, Bankless, M31 Capital, Airdrop Alert, Cryptopolitan) dans Gmail, parcourt les agrégateurs (CryptoRank, DropsTab, Airdrops.io), vérifie chaque opportunité sur le web avec Claude, note potentiel / effort / risque, et tient `TRACKER.md` à jour par compte.

Chaque matin (GitHub Actions), il revérifie les airdrops suivis, en ajoute de nouveaux et t'envoie un compte rendu par mail (`REPORT.md`) : d'abord « 🙋 À toi de jouer », les actions manuelles avec le pas-à-pas et le bouton vers le site officiel, puis le brief, les échéances, le wallet agent et les nouveautés.

Il pilote aussi un **wallet dédié** (`0x50F3347425617069E61a9A27Cbb8d645d19996f8`, Arbitrum + Base) : quand un airdrop suivi demande de l'activité on-chain, il fait lui-même le bridge ou le swap via LI.FI, le dépôt / retrait dans un vault (Aave USDC/WETH sur Base et Arbitrum, Spark USDC sur Base), ou le staking de HYPE sur Hyperliquid, sous plafonds, dès qu'une nouvelle newsletter arrive (vérifié toutes les 2 h), et le note dans le compte rendu. Les airdrops obtenus arrivent sur ce wallet.

## Sources

Abonne l'adresse Gmail de Chirac à ces newsletters ; il les lit toutes, avec le même filtrage :

| Newsletter | Motif d'expéditeur |
|---|---|
| [Le Grimoire du Mage](https://cryptomage.substack.com) | `cryptomage@substack.com` |
| [M31 Capital — The Monthly Airdrop](https://m31capital.substack.com) | `m31capital@substack.com` |
| [Bankless](https://www.bankless.com) | `bankless` |
| [Airdrop Alert](https://airdropalert.com/newsletter) | `airdropalert` |
| [Cryptopolitan — Airdrop Newsletter](https://www.cryptopolitan.com/airdrop-newsletter/) | `cryptopolitan` |

`NEWSLETTER_FROM=motif1,motif2` remplace cette liste. À chaque run il consulte aussi [CryptoRank Drophunting](https://cryptorank.io/drophunting), [DropsTab](https://dropstab.com/activities) et [Airdrops.io](https://airdrops.io), et X via la recherche web. Un nouvel airdrop n'est retenu qu'avec un site officiel vérifié et (airdrop confirmé, fonds levés connus ou deux sources indépendantes), 5 au plus par run ; le tracker indique où il a été vu.

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
| `HYPE_BUDGET_USD` | 50 | total maximum en HYPE (staké ou en route) sur Hyperliquid |

## Piloter l'agent

```bash
gh workflow run hunt.yml --repo sl11me/Sn0opyDr0p                    # lancer maintenant (agit s'il y a un nouveau mail)
gh workflow run hunt.yml --repo sl11me/Sn0opyDr0p -f force=true      # lancer et agir même sans nouveau mail
gh variable set AGENT_EXECUTE --body false --repo sl11me/Sn0opyDr0p  # arrêter : il ne signe plus rien
gh variable set AGENT_EXECUTE --body true --repo sl11me/Sn0opyDr0p   # rallumer
gh run list --workflow hunt.yml --repo sl11me/Sn0opyDr0p             # derniers runs
```

## Garde-fous on-chain

Agent automatique (`hunt --execute`) :

- Claude choisit dans un menu fermé : swap/bridge ETH ↔ USDC (Arbitrum ↔ Base), dépôt ou retrait dans un vault de `VAULTS`. Il n'écrit jamais de calldata : pour les swaps elle vient de LI.FI, pour les vaults elle est encodée par le code avec des ABI fixes (Aave `supply`/`withdraw`, ERC-4626 `deposit`/`withdraw`/`redeem`).
- Vaults : adresses vérifiées on-chain, et revérifiées avant chaque tx (sous-jacent, POOL Aave). Approbations au montant exact, jamais illimitées. Les retraits ne comptent pas dans le plafond du jour (ils rendent des fonds au wallet). Ajouter un vault = une PR.
- Avant de signer, le code vérifie : contrat = LI.FI Diamond, expéditeur **et** destinataire = wallet agent, montant exact, perte < 10 %, plafonds par tx et par jour, réserve de gas, airdrop suivi et actif. La tx est simulée (`estimate_gas`) avant envoi.
- Hyperliquid (`hype_stake`) : ETH Arbitrum → HYPE natif sur HyperEVM via LI.FI (même vérification de devis), envoi à l'adresse système `0x2222…2222` vers HyperCore, puis `cDeposit` et `tokenDelegate` signés par le wallet agent, chez le validateur actif, non jailé, commission ≤ 5 %, uptime ≥ 99 % qui a le plus gros stake. Reprend là où il s'est arrêté au run suivant. Stake bloqué 1 jour, sortie en 7 jours (à faire sur app.hyperliquid.xyz avec le wallet dans MetaMask).
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
