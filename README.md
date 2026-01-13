<!-- PROJECT SHIELDS -->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]


<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/polymarket/agents">
    <img src="docs/images/cli.png" alt="Logo" width="466" height="262">
  </a>

<h3 align="center">Polymarket Agents</h3>

  <p align="center">
    Trade autonomously on Polymarket using AI Agents
    <br />
    <a href="https://github.com/polymarket/agents"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/polymarket/agents">View Demo</a>
    ·
    <a href="https://github.com/polymarket/agents/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    ·
    <a href="https://github.com/polymarket/agents/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>


<!-- CONTENT -->
# Polymarket Agents

Polymarket Agents is a developer framework and set of utilities for building AI agents for Polymarket.

This code is free and publicly available under MIT License open source license ([terms of service](#terms-of-service))!

## Features

- Integration with Polymarket API
- AI agent utilities for prediction markets
- Local and remote RAG (Retrieval-Augmented Generation) support
- Data sourcing from betting services, news providers, and web search
- Comphrehensive LLM tools for prompt engineering

# Getting started

This repo is inteded for use with Python 3.9

1. Clone the repository

   ```
   git clone https://github.com/{username}/polymarket-agents.git
   cd polymarket-agents
   ```

2. Create the virtual environment

   ```
   virtualenv --python=python3.9 .venv
   ```

3. Activate the virtual environment

   - On Windows:

   ```
   .venv\Scripts\activate
   ```

   - On macOS and Linux:

   ```
   source .venv/bin/activate
   ```

4. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

5. Set up your environment variables:

   - Create a `.env` file in the project root directory

   ```
   cp .env.example .env
   ```

   - Add the following environment variables:

   ```
   POLYGON_WALLET_PRIVATE_KEY=""
   OPENAI_API_KEY=""
   XAI_API_KEY=""  # Optional: for Grok with X search (get from https://console.x.ai/)
   ```

6. Load your wallet with USDC.

7. Try the command line interface...

   ```
   python scripts/python/cli.py
   ```

   Or get AI trading recommendations:

   ```
   python agents/application/trade.py recommendations 10
   ```

   Or run the full autonomous trading flow:

   ```
   python agents/application/trade.py
   ```

8. Note: If running the command outside of docker, please set the following env var:

   ```
   export PYTHONPATH="."
   ```

   If running with docker is preferred, we provide the following scripts:

   ```
   ./scripts/bash/build-docker.sh
   ./scripts/bash/run-docker-dev.sh
   ```

## Architecture

The Polymarket Agents architecture features modular components that can be maintained and extended by individual community members.

### APIs

Polymarket Agents connectors standardize data sources and order types.

- `Chroma.py`: chroma DB for vectorizing news sources and other API data. Developers are able to add their own vector database implementations.

- `Gamma.py`: defines `GammaMarketClient` class, which interfaces with the Polymarket Gamma API to fetch and parse market and event metadata. Methods to retrieve current and tradable markets, as well as defined information on specific markets and events.

- `Polymarket.py`: defines a Polymarket class that interacts with the Polymarket API to retrieve and manage market and event data, and to execute orders on the Polymarket DEX. It includes methods for API key initialization, market and event data retrieval, and trade execution. The file also provides utility functions for building and signing orders, as well as examples for testing API interactions.

- `Objects.py`: data models using Pydantic; representations for trades, markets, events, and related entities.

## Data Flow

### Key Concepts

Before diving into the data flow, here's what the core technologies do:

| Term | What It Is |
|------|------------|
| **[Web3.py](https://github.com/ethereum/web3.py)** | Python library for interacting with Ethereum-compatible blockchains. It connects to nodes via RPC to query balances, send transactions, and call smart contracts. |
| **[Polygon RPC](https://chainlist.org/chain/137)** | Remote Procedure Call endpoint for the Polygon network (chain ID 137). Polygon is a Layer 2 scaling solution offering faster transactions and lower fees than Ethereum mainnet. |
| **[CLOB](https://docs.polymarket.com/developers/CLOB/introduction)** | Central Limit Order Book - Polymarket's hybrid-decentralized exchange. Orders are matched off-chain for speed, but settled on-chain for security. Uses signed messages so funds stay in your wallet until trades execute. |
| **[ERC20 (USDC)](https://polygonscan.com/token/0x2791bca1f2de4661ed88a30c99a7a9449aa84174)** | Token standard for fungible assets. USDC is a dollar-backed stablecoin issued by Circle. On Polygon, it's used as collateral for prediction market trades. |
| **[ERC1155 (CTF)](https://docs.polymarket.com/developers/CTF/overview)** | Multi-token standard used by Gnosis Conditional Token Framework. Each prediction market outcome (YES/NO) becomes a distinct token. When you buy "YES" shares, you receive ERC1155 tokens redeemable for USDC if correct. |
| **[Gamma API](https://docs.polymarket.com/developers/gamma-markets-api/overview)** | Polymarket's indexed market data service. Provides market metadata, prices, volumes, and event information via REST API. Read-only - does not execute trades. |
| **[ChromaDB](https://docs.trychroma.com/)** | Open-source vector database for AI applications. Stores embeddings (numerical representations of text) and enables semantic similarity search for RAG (Retrieval-Augmented Generation). |
| **[OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)** | API that converts text into numerical vectors. Uses `text-embedding-3-small` model to represent market descriptions for similarity search. |

### Startup Initialization

When the application starts, components initialize in this order:

```
1. Load .env file (python-dotenv)
   └─► POLYGON_WALLET_PRIVATE_KEY, OPENAI_API_KEY, etc.

2. Initialize Polymarket()
   ├─► Web3 connection → Polygon RPC (polygon-rpc.com)
   ├─► CLOB Client for order submission (clob.polymarket.com)
   ├─► ERC20 (USDC) contract connection
   └─► ERC1155 (CTF) conditional token contract

3. Initialize GammaMarketClient()
   └─► HTTP client for Gamma API (gamma-api.polymarket.com)

4. Initialize Executor()
   ├─► ChatOpenAI LLM (gpt-3.5-turbo-16k)
   ├─► Prompter (AI prompt templates)
   └─► PolymarketRAG (Chroma + OpenAI embeddings)

5. Initialize News() [optional]
   └─► NewsAPI client for news retrieval
```

### Main Trading Flow (`one_best_trade`)

The autonomous trading flow works as follows:

```
START: Trader.one_best_trade()
  │
  ├─► Fetch all tradeable events from Gamma API
  │   └─► GET https://gamma-api.polymarket.com/events
  │
  ├─► Filter events with RAG
  │   ├─► Embed events with OpenAI text-embedding-3-small
  │   ├─► Store in Chroma vector database
  │   └─► Similarity search for profitable opportunities
  │
  ├─► Map filtered events → Markets
  │   └─► GET https://gamma-api.polymarket.com/markets/{id}
  │
  ├─► Filter markets with RAG
  │   └─► Find most profitable trading opportunities
  │
  ├─► Source best trade (LLM analysis)
  │   ├─► LLM Call #1: Superforecaster prediction
  │   │   └─► "I believe {question} has likelihood {0.x} for {outcome}"
  │   └─► LLM Call #2: Trade execution decision
  │       └─► "price:X, size:Y, side:BUY/SELL"
  │
  ├─► Format trade (calculate size from USDC balance)
  │
  ├─► Execute trade via CLOB (if enabled)
  │   └─► POST to https://clob.polymarket.com
  │
  └─► Save results → ./results/one_best_trade_{timestamp}.json
```

### Recommendations Flow (`get_recommendations`)

A simplified flow that generates AI trading recommendations without the full RAG pipeline:

```
START: Trader.get_recommendations(limit=10, max_days_until_expiry=7)
  │
  ├─► Fetch active markets from Gamma API
  │   └─► GET https://gamma-api.polymarket.com/markets?closed=false&active=true
  │
  ├─► Filter markets (optional: by expiration date)
  │   └─► Only include markets expiring within max_days_until_expiry
  │
  ├─► For each market:
  │   ├─► Get AI superforecaster prediction
  │   │   └─► LLM predicts probability for "Yes" outcome
  │   ├─► Compare AI prediction vs market price
  │   └─► Calculate edge (AI% - Market%)
  │
  ├─► Generate signals:
  │   ├─► BUY YES if edge > +15%
  │   ├─► BUY NO if edge < -15%
  │   └─► HOLD otherwise
  │
  └─► Save results → ./results/recommendations_{timestamp}.json
```

**Usage:**
```bash
# Get recommendations for 10 markets (default, uses GPT-3.5)
python agents/application/trade.py recommendations

# Get recommendations for specific number of markets
python agents/application/trade.py recommendations 20

# Get recommendations for markets expiring within 7 days
python agents/application/trade.py recommendations 10 7

# Get recommendations for markets expiring tomorrow (1 day)
python agents/application/trade.py recommendations 10 1

# Use Grok with X search for real-time predictions (requires XAI_API_KEY)
python agents/application/trade.py recommendations 10 --grok

# Combine expiry filter with Grok
python agents/application/trade.py recommendations 10 7 --grok
```

**AI Models:**
| Model | Flag | Features |
|-------|------|----------|
| GPT-3.5 | (default) | Fast, uses training data only |
| Grok | `--grok` | Real-time X search + web search |

**Output format:**
```json
{
  "timestamp": "2024-01-12T22:23:54",
  "total_markets_analyzed": 10,
  "recommendations": [
    {
      "market_id": "12345",
      "question": "Will X happen?",
      "market_yes_price": 25.0,
      "ai_prediction": 75.0,
      "edge": 50.0,
      "signal": "BUY YES",
      "end_date": "2024-01-15T00:00:00Z",
      "days_until_expiry": 3
    }
  ]
}
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLI / Entry Points                    │
│  (cli.py, trade.py, creator.py, server.py, cron.py)    │
└────────────────────────────┬────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
    ┌─────────┐        ┌──────────┐        ┌──────────┐
    │ Trader  │        │ Creator  │        │ Executor │
    └────┬────┘        └────┬─────┘        └────┬─────┘
         │                  │                   │
    ┌────┴──────────────────┴───────────────────┴────┐
    │                                                 │
    ▼                   ▼                   ▼         ▼
┌───────────┐   ┌─────────────┐   ┌──────────┐  ┌─────────────┐
│Polymarket │   │GammaMarket  │   │ChatOpenAI│  │PolymarketRAG│
│(Web3+CLOB)│   │Client (API) │   │  (LLM)   │  │  (Chroma)   │
└─────┬─────┘   └──────┬──────┘   └────┬─────┘  └──────┬──────┘
      │                │               │               │
      ▼                ▼               ▼               ▼
  Polygon RPC     Gamma API       OpenAI API     Local Vector DB
```

### External Services

| Service | URL | Purpose |
|---------|-----|---------|
| [Polygon RPC](https://chainlist.org/chain/137) | `polygon-rpc.com` | Blockchain queries (chain ID 137) |
| [Gamma API](https://docs.polymarket.com/developers/gamma-markets-api/overview) | `gamma-api.polymarket.com` | Market/event data |
| [CLOB API](https://docs.polymarket.com/developers/CLOB/introduction) | `clob.polymarket.com` | Order submission |
| [OpenAI](https://platform.openai.com/docs/guides/embeddings) | `api.openai.com` | LLM (gpt-3.5-turbo-16k) + Embeddings (text-embedding-3-small) |

### Key Files

| Component | File | Purpose |
|-----------|------|---------|
| Core Trading | `agents/polymarket/polymarket.py` | Web3 + CLOB trading interface |
| Market Data | `agents/polymarket/gamma.py` | Gamma API client |
| AI Orchestrator | `agents/application/executor.py` | LLM + RAG coordination |
| Vector DB | `agents/connectors/chroma.py` | ChromaDB RAG operations |
| Prompts | `agents/application/prompts.py` | AI prompt templates |
| Data Models | `agents/utils/objects.py` | Pydantic models |
| CLI | `scripts/python/cli.py` | Command-line interface |
| Trade Entry | `agents/application/trade.py` | Trading commands (recommendations, one_best_trade) |

### Scripts

Files for managing your local environment, server set-up to run the application remotely, and cli for end-user commands.

`cli.py` is the primary user interface for the repo. Users can run various commands to interact with the Polymarket API, retrieve relevant news articles, query local data, send data/prompts to LLMs, and execute trades in Polymarkets.

Commands should follow this format:

`python scripts/python/cli.py command_name [attribute value] [attribute value]`

Example:

`get-all-markets`
Retrieve and display a list of markets from Polymarket, sorted by volume.

   ```
   python scripts/python/cli.py get-all-markets --limit <LIMIT> --sort-by <SORT_BY>
   ```

- limit: The number of markets to retrieve (default: 5).
- sort_by: The sorting criterion, either volume (default) or another valid attribute.

# Contributing

If you would like to contribute to this project, please follow these steps:

1. Fork the repository.
2. Create a new branch.
3. Make your changes.
4. Submit a pull request.

Please run pre-commit hooks before making contributions. To initialize them:

   ```
   pre-commit install
   ```

# Related Repos

- [py-clob-client](https://github.com/Polymarket/py-clob-client): Python client for the Polymarket CLOB
- [python-order-utils](https://github.com/Polymarket/python-order-utils): Python utilities to generate and sign orders from Polymarket's CLOB
- [Polymarket CLOB client](https://github.com/Polymarket/clob-client): Typescript client for Polymarket CLOB
- [Langchain](https://github.com/langchain-ai/langchain): Utility for building context-aware reasoning applications
- [Chroma](https://docs.trychroma.com/getting-started): Chroma is an AI-native open-source vector database

# Prediction markets reading

- Prediction Markets: Bottlenecks and the Next Major Unlocks, Mikey 0x: https://mirror.xyz/1kx.eth/jnQhA56Kx9p3RODKiGzqzHGGEODpbskivUUNdd7hwh0
- The promise and challenges of crypto + AI applications, Vitalik Buterin: https://vitalik.eth.limo/general/2024/01/30/cryptoai.html
- Superforecasting: How to Upgrade Your Company's Judgement, Schoemaker and Tetlock: https://hbr.org/2016/05/superforecasting-how-to-upgrade-your-companys-judgment

# License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/Polymarket/agents/blob/main/LICENSE.md) file for details.

# Contact

For any questions or inquiries, please contact liam@polymarket.com or reach out at www.greenestreet.xyz

Enjoy using the CLI application! If you encounter any issues, feel free to open an issue on the repository.

# Terms of Service

[Terms of Service](https://polymarket.com/tos) prohibit US persons and persons from certain other jurisdictions from trading on Polymarket (via UI & API and including agents developed by persons in restricted jurisdictions), although data and information is viewable globally.


<!-- LINKS -->
[contributors-shield]: https://img.shields.io/github/contributors/polymarket/agents?style=for-the-badge
[contributors-url]: https://github.com/polymarket/agents/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/polymarket/agents?style=for-the-badge
[forks-url]: https://github.com/polymarket/agents/network/members
[stars-shield]: https://img.shields.io/github/stars/polymarket/agents?style=for-the-badge
[stars-url]: https://github.com/polymarket/agents/stargazers
[issues-shield]: https://img.shields.io/github/issues/polymarket/agents?style=for-the-badge
[issues-url]: https://github.com/polymarket/agents/issues
[license-shield]: https://img.shields.io/github/license/polymarket/agents?style=for-the-badge
[license-url]: https://github.com/polymarket/agents/blob/master/LICENSE.md
