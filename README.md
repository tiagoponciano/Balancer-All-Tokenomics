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

### Data hosting (NEON) – recommended for the Streamlit app

The final CSVs can be too large for Supabase Storage. Hosting the data in **NEON** (serverless Postgres) avoids size limits and lets the app load data from the database.

- **NEON Launch plan**: usage-based ($0.106/CU-hour compute, $0.35/GB-month storage); no monthly minimum. A ~100k-row table is typically well under 1 GB.
- **Flow**: Run the pipeline (e.g. monthly), then upload to NEON. The Streamlit app reads from NEON when `DATABASE_URL` is set.

#### How to create your NEON database

1. **Sign up / log in**  
   Go to [neon.tech](https://neon.tech) and sign up (or log in with GitHub).

2. **Create a project**  
   - Click **New Project**.  
   - Choose a name (e.g. `balancer-tokenomics`), region (pick one close to you or your users), and Postgres version (e.g. 16).  
   - Click **Create project**.

3. **Get the connection string**  
   - On the project dashboard, open the **Connection details** panel.  
   - Select **Pooled connection** (recommended for serverless/Streamlit).  
   - Copy the connection string; it looks like:  
     `postgresql://USER:PASSWORD@ep-xxx-xxx.region.aws.neon.tech/neondb?sslmode=require`  
   - (Optional) You can create a dedicated database or role from the **Databases** / **Roles** tabs; the default `neondb` and your user are enough to start.)

4. **Add it to `.env`**  
   In your project root, in `.env` add:
   ```env
   DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
   ```
5. **Upload data**  
   After generating the final dataset, upload to NEON:
   ```bash
   python main.py --upload-to-neon
   ```
   Or run the full pipeline; if `DATABASE_URL` is set, the upload runs automatically at the end.
6. **Run or deploy Streamlit** with the same `DATABASE_URL`. The app will load from NEON first, then fall back to local CSV or Supabase.

**To run Streamlit so it uses NEON:** ensure `DATABASE_URL` is in your `.env` (project root), then from the project root run:
```bash
streamlit run script/home.py
```
The app loads `.env` from the project root. When data comes from NEON, the sidebar shows **"Data: NEON"**.

#### Running with **full data** (Streamlit Cloud memory limit)

Streamlit Cloud has a ~1 GB memory limit. Loading the full dataset (100k+ rows) can exceed it. **You don’t need to change to fullstack.** Deploy the same Streamlit app on a host with more RAM (e.g. Railway, Render, Fly.io, or a VPS). See **[DEPLOYMENT.md](DEPLOYMENT.md)** for step-by-step options and an optional API backend.

#### Monthly incremental runs

When you rerun the pipeline **without** `--start-date` / `--end-date`, the script uses **incremental** dates:

- **Start date** = day after the last date already in your data (from NEON `tokenomics` table or from local `data/Balancer-All-Tokenomics.csv` / `Balancer-All-Tokenomics-Organized.csv`).
- **End date** = today.

So if the last register was `2026-02-09`, the next run will fetch from `2026-02-10` to today. The new veBAL chunk is **merged** with your existing `veBAL.csv` (no history loss), then the rest of the pipeline runs and the final dataset is uploaded to NEON.

To disable incremental and always use a fixed range, set in `.env`:
```env
INCREMENTAL=0
```
Then use `--start-date` and `--end-date` explicitly, or rely on `START_DATE` / `END_DATE` env vars.

To run only the upload (e.g. after re-running `--create-final`):

```bash
python main.py --upload-to-neon
```

## 🎯 Usage

### Quick Start - Generate Datasets

If you already have all the required data files and just want to generate the final datasets:

```bash
python generate_datasets.py
```

This will generate both output files:
- `data/Balancer-All-Tokenomics.csv` (ALL version)
- `data/Balancer-All-Tokenomics-Organized.csv` (ORGANIZED version)

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
7. Final dataset creation (generates BOTH output files)

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

# Upload final CSV to NEON (requires DATABASE_URL in .env)
python main.py --upload-to-neon

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

The final dataset generation creates **TWO output files**:

1. **`Balancer-All-Tokenomics.csv`** (ALL VERSION)
   - Contains **ALL records** from veBAL
   - Includes pools without votes/bribes data
   - Enriched with FSN_data mappings for gauge_address and blockchain
   - Best for comprehensive analysis

2. **`Balancer-All-Tokenomics-Organized.csv`** (ORGANIZED VERSION)
   - Contains **only complete records** with votes/bribes data
   - Filtered to records with gauge_address
   - Best for focused analysis and dashboards

Both datasets combine:
- veBAL data (TVL, fees, volumes, etc.)
- Votes & Bribes data (when available)
- **Core/Non-Core Classification** based on time intervals
- **FSN_data enrichment** for gauge addresses and chain mappings

## 📁 Generated Files Structure

```
data/
├── veBAL.csv                                    # veBAL data from Dune (all pools, all dates)
├── FSN_data.csv                                 # Gauge and chain mappings
├── Bribes.csv                                   # Bribes from Dune
├── Votes_Emissions.csv                          # Votes and Emissions from Dune
├── votes_bribes_merged.csv                      # Votes + Bribes Merge
├── classification_core_pools.csv                # Core/Non-Core Classification
├── Balancer-All-Tokenomics.csv                  # 🎯 ALL records (comprehensive)
└── Balancer-All-Tokenomics-Organized.csv        # 🎯 Complete records only (focused)
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
| `swap_fee_percent` | Swap fee percentage |
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

## ❓ Which Dataset Should I Use?

### Use `Balancer-All-Tokenomics.csv` (ALL) when:
- ✅ You need a comprehensive view of all pools on all dates
- ✅ You want to analyze pools without active voting/bribes
- ✅ You're doing historical analysis or pool tracking
- ✅ You want to see the full picture including incomplete data

### Use `Balancer-All-Tokenomics-Organized.csv` (ORGANIZED) when:
- ✅ You only care about pools with votes/bribes activity
- ✅ You're building dashboards focused on active pools
- ✅ You want cleaner data without missing values
- ✅ You're analyzing ROI or bribe efficiency metrics

**Note:** The Streamlit app uses the ALL version by default, giving you the most comprehensive view.

## 🐛 Troubleshooting

### Error: "DUNE_API_KEY not found"
- Check if the `.env` file exists in the project root
- Confirm that the key is correctly configured

### Error: "File not found: FSN_data.csv"
- Run the full pipeline first: `python main.py`
- Ensure all required data files exist in `data/` folder
- Verify that veBAL.csv is the NEW version with all dates

### Error: "File not found"
- Run the full pipeline first: `python main.py`
- Check if input files exist in `data/`

### Core Pools Classification not working
- Check if `data/results.csv` exists and has columns: `address`, `added_date`, `removed_date`
- Confirm that `data/veBAL.csv` has `project_contract_address` and `block_date`

### Missing or lower bribes than expected
- Ensure you're using the NEW `veBAL.csv` file with all dates (not the old audited version)
- Verify that `FSN_data.csv` is up to date with latest gauge mappings
- Check the console output during final dataset creation for merge statistics
- Compare totals between ALL and ORGANIZED versions

### Need more details?
- See `CHANGES_SUMMARY.md` for detailed information about the data processing changes
- Run `python generate_datasets.py` to see detailed statistics during generation
