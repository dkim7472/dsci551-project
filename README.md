# Portfolio Risk Snapshot & What-If Scenario Simulation

**DSCI 551 Course Project — Spring 2026**  
**Author:** David Kim  
**Database:** PostgreSQL  
**Focus Area:** MVCC (Multi-Version Concurrency Control) & Snapshot Isolation

---

## Project Overview

This project demonstrates how PostgreSQL's MVCC mechanism enables consistent data views and safe experimentation in a financial portfolio management context. The application has three features:

1. **Portfolio Risk Snapshot:** Computes portfolio value, sector exposure, and unrealized P&L using PostgreSQL's REPEATABLE READ isolation level to guarantee consistent reads across multiple queries.

2. **What-If Scenario Simulation:** Simulates hypothetical market changes (e.g., "What if tech stocks drop 20%?") by applying temporary price updates inside a transaction, recalculating metrics, then rolling back. MVCC ensures no data is permanently changed.

3. **MVCC Concurrent Access Demo:** Opens two separate database connections and shows that an uncommitted UPDATE on one connection is invisible to the other connection. This directly demonstrates how PostgreSQL uses row versioning to isolate transactions.

---

## Prerequisites

- PostgreSQL 13 or higher
- Python 3.9 or higher
- psycopg2-binary (Python package)

---

## How to Download and Run This Project

### Step 1: Clone the Repository

Open a terminal (Command Prompt, PowerShell, or Terminal) and run:

```bash
git clone https://github.com/dkim7472/dsci551-project.git
cd dsci551-project
```

### Step 2: Make Sure PostgreSQL is Running

- **Windows:** Open the Start menu, search for "pgAdmin" or "Services" and make sure the PostgreSQL service is running.
- **macOS:** Run `brew services start postgresql@16`
- **Ubuntu:** Run `sudo systemctl start postgresql`

### Step 3: Create the Database

```bash
psql -U postgres -c "CREATE DATABASE portfolio_risk;"
```

If prompted for a password, enter your PostgreSQL password (default is usually `postgres`).

### Step 4: Load the Schema and Sample Data

```bash
psql -U postgres -d portfolio_risk -f sql/schema_and_seed.sql
```

This creates:
- 4 tables: portfolios, assets, positions, prices
- 2 views: latest_prices, portfolio_holdings
- 2 indexes for efficient queries
- Sample data: 12 assets across 6 sectors, 2 portfolios with positions, and market prices

### Step 5: Install the Python Dependency

```bash
pip install psycopg2-binary
```

### Step 6: Update the Database Connection (if needed)

Open `app.py` in any text editor. At the top, you'll see:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "dbname": "portfolio_risk",
    "user": "postgres",
    "password": "postgres",
}
```

If your PostgreSQL username, password, or port are different, update them here.

### Step 7: Run the Application

```bash
python app.py
```

You should see a menu with three options:
1. Portfolio Risk Snapshot
2. What-If Scenario Simulation
3. MVCC Concurrent Access Demo

---

## Database Schema

- **portfolios** — Portfolio metadata (portfolio_id, name, owner, created_at)
- **assets** — Financial instruments (asset_id, symbol, name, sector, asset_type)
- **positions** — Holdings linking portfolios to assets (position_id, portfolio_id, asset_id, quantity, avg_cost)
- **prices** — Market prices with timestamps (price_id, asset_id, price, as_of)

**Views:**
- **latest_prices** — Most recent price per asset using DISTINCT ON
- **portfolio_holdings** — Joined view computing market values and unrealized P&L

**Indexes:**
- `idx_prices_asset_as_of` on prices(asset_id, as_of DESC) for efficient latest-price lookups
- `idx_positions_portfolio` on positions(portfolio_id) for fast portfolio queries
---
