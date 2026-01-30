# Balancer-All-Tokenomics

Automated system for collecting and analyzing tokenomics data from the Balancer Protocol.

## 🚀 Features

- ✅ Automatic data collection from Dune Analytics
- ✅ Data collection from HiddenHand Finance
- ✅ Merge and consolidation of multiple data sources
- ✅ Core/Non-Core pool classification
- ✅ Final consolidated report generation
- ✅ **Weekly automation via GitHub Actions**
- ✅ **Automatic email report delivery**

## 📋 Installation

```bash
pip install -r requirements.txt
```

## 🔧 Configuration

1. Create a `.env` file in the project root:
```env
DUNE_API_KEY=your_key_here
EMAIL_FROM=your_email@gmail.com
EMAIL_PASSWORD=app_password
EMAIL_TO=recipient@email.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

2. For weekly automation, configure secrets on GitHub (see [SETUP_GITHUB_ACTIONS.md](SETUP_GITHUB_ACTIONS.md))

## 🎯 Usage

### Run complete pipeline:
```bash
python script/main.py
```

### Run individual steps:
```bash
python script/main.py --dune-only          # Only Dune queries
python script/main.py --hiddenhand-only    # Only HiddenHand
python script/main.py --merge-bribes       # Merge Bribes
python script/main.py --add-gauge          # Add gauge_address
python script/main.py --merge-votes-bribes # Merge Votes + Bribes
python script/main.py --create-final       # Create final dataset
```

## 📊 Generated Files

- `data/veBAL.csv` - veBAL data
- `data/Bribes.csv` - Bribes data (combined Dune + HiddenHand)
- `data/Votes_Emissions.csv` - Votes and Emissions data
- `data/votes_bribes_merged.csv` - Merge of Votes and Bribes
- `data/Balancer-All-Tokenomics.csv` - **Final consolidated dataset**

## 🤖 Automation

The system can be configured to run automatically every week via GitHub Actions and send the report by email.
