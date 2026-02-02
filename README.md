# Balancer-All-Tokenomics

Automated system for collecting, processing, and analyzing tokenomics data from the Balancer protocol.

## 🚀 Features

- ✅ **Automatic data collection from Dune Analytics** (veBAL, Bribes, Votes & Emissions)
- ✅ **Metadata collection from HiddenHand Finance** (pool names, derived addresses)
- ✅ **Intelligent Core/Non-Core pool classification** based on historical time intervals
- ✅ **Bribe enrichment** with additional metadata from HiddenHand
- ✅ **Merging and consolidation of multiple data sources**
- ✅ **Generation of a consolidated final dataset** with all metrics


## 📋 Prerequisites

- Python 3.8+
- Dune Analytics API Key
- Email credentials (for automation)

## 🔧 Installation

```bash
# Clone the repository
git clone <repository-url>
cd Balancer-All-Tokenomics

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Configuration

1. Create a `.env` file in the project root:

```env
DUNE_API_KEY=your_dune_api_key_here
SMTP_PORT=587
```

2. For weekly automation, configure secrets in GitHub Actions (see GitHub Actions documentation)

## 🎯 Usage

### Run complete pipeline:

```bash
python main.py
```

This will execute all steps in the correct order:
1. Data collection from Dune Analytics (source of truth for bribes)
2. Metadata collection from HiddenHand Finance (pool names, addresses)
3. Bribe enrichment: Add HiddenHand metadata to Dune bribes (LEFT JOIN)
4. Adding gauge_address to veBAL
5. Votes & Bribes merge
6. Core Pools Classification
7. Final dataset creation

### Run individual steps:

```bash
# Dune queries only
python main.py --dune-only

# HiddenHand collection only
python main.py --hiddenhand-only

# Bribes merge only
python main.py --merge-bribes

# Add gauge_address to veBAL
python main.py --add-gauge

# Votes & Bribes merge
python main.py --merge-votes-bribes

# Classify Core Pools
python main.py --classify-core-pools

# Create final dataset
python main.py --create-final

# View help
python main.py --help
```

## 📊 Data Pipeline

### 1. Data Collection

#### Dune Analytics Queries
- **Query 6623057**: `veBAL.csv` - veBAL data, TVL, fees, etc.
- **Query 6583834**: `Bribes.csv` - Bribes data from Dune
- **Query 6608301**: `Votes_Emissions.csv` - Votes and BAL emissions data

#### HiddenHand Finance
- Collection of **metadata only** via API (pool_name, pool_id, derived_pool_address)
- **IMPORTANT**: HiddenHand does NOT provide bribe amounts (amount_usdc)
- **Role**: Enrichment source to add pool metadata to Dune bribes
- Merge strategy: LEFT JOIN (preserves ALL Dune bribes, adds metadata where available)

### 2. Processing and Enrichment

#### Adding Gauge Address
- Adds `gauge_address` to the veBAL dataset based on `FSN_data.csv`
- Removes rows without a valid gauge_address

#### Votes & Bribes Merge
- Combines `Votes_Emissions.csv` and `Bribes.csv`
- Merge based on `gauge_address`, `day`, and `blockchain`

### 3. Core Pools Classification

**Classification Logic:**

A pool is classified as a **Core Pool** on a specific date if there exists at least one historical interval where:

- `added_date <= date` **AND**
- (`removed_date IS NULL` **OR** `removed_date > date`)

**Features:**
- ✅ Supports multiple periods (a pool can be core, then non-core, then core again)
- ✅ Based on historical time intervals, not fixed flags
- ✅ Uses only the **first 42 characters** of the address for matching (Ethereum address compatible)

**Required Files:**
- `data/results.csv` - Core pools history with columns: `address`, `added_date`, `removed_date`
- `data/veBAL.csv` - Daily dataset with `project_contract_address` and `block_date`

**Output:**
- `data/classification_core_pools.csv` - Classification by (address, day) with column `is_core` (True/False)

### 4. Final Dataset

The final dataset (`Balancer-All-Tokenomics.csv`) combines:
- veBAL data (TVL, fees, volumes, etc.)
- Votes & Bribes data
- **Core/Non-Core Classification** based on time intervals

## 📁 Generated Files Structure

```
data/
├── veBAL.csv                          # veBAL data from Dune
├── Bribes.csv                         # Bribes from Dune
├── Votes_Emissions.csv                # Votes and Emissions from Dune
├── votes_bribes_merged.csv            # Votes + Bribes Merge
├── classification_core_pools.csv      # Core/Non-Core Classification
└── Balancer-All-Tokenomics.csv        # 🎯 Consolidated final dataset
```

## 📋 Final Dataset Columns

The `Balancer-All-Tokenomics.csv` file contains the following columns:

| Column | Description |
|--------|-------------|
| `blockchain` | Blockchain (ethereum, arbitrum, etc.) |
| `project` | Project/pool name |
| `version` | Pool version |
| `block_date` | Record date |
| `project_contract_address` | Pool contract address |
| `gauge_address` | Associated gauge address |
| `pool_symbol` | Pool symbol |
| `pool_type` | Pool type |
| `swap_amount_usd` | Swap volume in USD |
| `tvl_usd` | TVL in USD |
| `tvl_eth` | TVL in ETH |
| `total_protocol_fee_usd` | Total protocol fee in USD |
| `protocol_fee_amount_usd` | Protocol fee amount in USD |
| `swap_fee_usd` | Swap fee in USD |
| `yield_fee_usd` | Yield fee in USD |
| `swap_fee_%` | Swap fee percentage |
| `core_non_core` | Core/Non-Core Classification (Core/Non-Core) |
| `bal_emited_votes` | BAL emitted via votes |
| `votes_received` | Votes received |
| `bribe_amount_usd` | Bribe amount in USD |

## 🔍 Technical Details

### Core Pools Classification

The classification uses a **time interval-based** approach, allowing pools to have multiple periods as a Core Pool over time.

**Example:**
```
Pool A:
- added_date: 2024-01-01, removed_date: 2024-03-01  → Core from 01/01 to 01/03
- added_date: 2024-05-10, removed_date: NULL        → Core from 05/10 onwards

Result:
- 2024-02-01 → ✅ Core Pool
- 2024-04-01 → ❌ Non-Core Pool
- 2024-06-01 → ✅ Core Pool
```

### Address Matching

To ensure compatibility between different address formats:
- Uses only the **first 42 characters** for matching
- Converts to lowercase and removes whitespace
- Compatible with standard Ethereum addresses (0x + 40 hex digits)


## 📝 Available Scripts

| Script | Description |
|--------|-------------|
| `main.py` | Main script - orchestrates the entire pipeline |
| `script/dune_fetcher.py` | Data collection from Dune Analytics |
| `script/fetch_hiddenhand.py` | Data collection from HiddenHand Finance |
| `script/merge_bribes.py` | Enriches Dune bribes with HiddenHand metadata (LEFT JOIN) |
| `script/add_gauge_address.py` | Adds gauge_address to veBAL |
| `script/merge_votes_bribes.py` | Votes & Bribes Merge |
| `script/classify_core_pools.py` | Core/Non-Core pools classification |
| `script/create_final_dataset.py` | Consolidated final dataset creation |

## 🐛 Troubleshooting

### Error: "DUNE_API_KEY not found"
- Check if the `.env` file exists in the project root
- Confirm that the key is correctly configured

### Error: "File not found"
- Run the full pipeline first: `python main.py`
- Check if input files exist in `data/`

### Core Pools Classification not working
- Check if `data/results.csv` exists and has columns: `address`, `added_date`, `removed_date`
- Confirm that `data/veBAL.csv` has `project_contract_address` and `block_date`

