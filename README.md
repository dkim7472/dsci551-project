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

## Setup Instructions

### 1. Install PostgreSQL

- **Windows:** Download from https://www.postgresql.org/download/windows/
- **macOS:** `brew install postgresql@16`
- **Ubuntu:** `sudo apt install postgresql`

Make sure PostgreSQL is running.

### 2. Create the Database

```bash
psql -U postgres -c "CREATE DATABASE portfolio_risk;"
```

### 3. Run the Schema and Seed Data

```bash
psql -U postgres -d portfolio_risk -f sql/schema_and_seed.sql
```

This creates four tables (portfolios, assets, positions, prices), two views (latest_prices, portfolio_holdings), indexes, and populates the database with sample data including 12 assets across 6 sectors and 2 portfolios.

### 4. Install Python Dependencies

```bash
pip install psycopg2-binary
```

### 5. Configure Database Connection

Open `app.py` and update `DB_CONFIG` if your PostgreSQL settings differ from the defaults:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "dbname": "portfolio_mvcc",
    "user": "postgres",
    "password": "postgres",
}
```

### 6. Run the Application

```bash
python app.py
```

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
