-- DSCI 551 Project: Portfolio Risk Snapshot & What-If Simulation
-- Database: PostgreSQL
-- Focus: MVCC (Multi-Version Concurrency Control) & Snapshot Isolation
-- Author: David Kim

-- Drop tables if they exist (for clean re-runs)
DROP TABLE IF EXISTS prices CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS assets CASCADE;
DROP TABLE IF EXISTS portfolios CASCADE;


-- 1. SCHEMA DEFINITION


-- Portfolios table
CREATE TABLE portfolios (
    portfolio_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    owner VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assets table: financial instruments
CREATE TABLE assets (
    asset_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    sector VARCHAR(50) NOT NULL,
    asset_type VARCHAR(30) NOT NULL  -- 'stock', 'etf', 'bond'
);

-- Positions table: holdings in a portfolio
CREATE TABLE positions (
    position_id SERIAL PRIMARY KEY,
    portfolio_id INT NOT NULL REFERENCES portfolios(portfolio_id),
    asset_id INT NOT NULL REFERENCES assets(asset_id),
    quantity NUMERIC(12,4) NOT NULL,
    avg_cost NUMERIC(12,4) NOT NULL,  -- average purchase price
    UNIQUE(portfolio_id, asset_id)
);

-- Prices table: market prices with timestamps
CREATE TABLE prices (
    price_id SERIAL PRIMARY KEY,
    asset_id INT NOT NULL REFERENCES assets(asset_id),
    price NUMERIC(12,4) NOT NULL,
    as_of TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index on prices for fast latest-price lookups
CREATE INDEX idx_prices_asset_as_of ON prices(asset_id, as_of DESC);

-- Index on positions for portfolio lookups
CREATE INDEX idx_positions_portfolio ON positions(portfolio_id);

-- 2. SEED DATA

-- Insert portfolios
INSERT INTO portfolios (name, owner) VALUES
    ('Growth Portfolio', 'David Kim'),
    ('Conservative Portfolio', 'David Kim');

-- Insert assets
INSERT INTO assets (symbol, name, sector, asset_type) VALUES
    ('AAPL', 'Apple Inc.', 'Technology', 'stock'),
    ('MSFT', 'Microsoft Corp.', 'Technology', 'stock'),
    ('GOOGL', 'Alphabet Inc.', 'Technology', 'stock'),
    ('AMZN', 'Amazon.com Inc.', 'Technology', 'stock'),
    ('JPM', 'JPMorgan Chase & Co.', 'Finance', 'stock'),
    ('BAC', 'Bank of America Corp.', 'Finance', 'stock'),
    ('JNJ', 'Johnson & Johnson', 'Healthcare', 'stock'),
    ('PFE', 'Pfizer Inc.', 'Healthcare', 'stock'),
    ('XOM', 'Exxon Mobil Corp.', 'Energy', 'stock'),
    ('NEE', 'NextEra Energy Inc.', 'Energy', 'stock'),
    ('SPY', 'SPDR S&P 500 ETF', 'Index', 'etf'),
    ('AGG', 'iShares Core US Aggregate Bond', 'Fixed Income', 'bond');

-- Insert positions for Growth Portfolio
INSERT INTO positions (portfolio_id, asset_id, quantity, avg_cost) VALUES
    (1, 1, 50, 145.00),    -- 50 shares AAPL
    (1, 2, 30, 280.00),    -- 30 shares MSFT
    (1, 3, 20, 120.00),    -- 20 shares GOOGL
    (1, 4, 15, 130.00),    -- 15 shares AMZN
    (1, 5, 40, 140.00),    -- 40 shares JPM
    (1, 7, 25, 160.00),    -- 25 shares JNJ
    (1, 9, 35, 95.00),     -- 35 shares XOM
    (1, 11, 100, 420.00),  -- 100 shares SPY
    (1, 12, 200, 98.00);   -- 200 shares AGG

-- Insert positions for Conservative Portfolio
INSERT INTO positions (portfolio_id, asset_id, quantity, avg_cost) VALUES
    (2, 5, 60, 135.00),    -- 60 shares JPM
    (2, 6, 80, 32.00),     -- 80 shares BAC
    (2, 7, 50, 155.00),    -- 50 shares JNJ
    (2, 8, 100, 38.00),    -- 100 shares PFE
    (2, 10, 45, 72.00),    -- 45 shares NEE
    (2, 11, 150, 415.00),  -- 150 shares SPY
    (2, 12, 500, 97.00);   -- 500 shares AGG

-- Insert current market prices
INSERT INTO prices (asset_id, price, as_of) VALUES
    (1, 178.50, CURRENT_TIMESTAMP),    -- AAPL
    (2, 415.20, CURRENT_TIMESTAMP),    -- MSFT
    (3, 155.80, CURRENT_TIMESTAMP),    -- GOOGL
    (4, 185.60, CURRENT_TIMESTAMP),    -- AMZN
    (5, 195.40, CURRENT_TIMESTAMP),    -- JPM
    (6, 37.80, CURRENT_TIMESTAMP),     -- BAC
    (7, 162.30, CURRENT_TIMESTAMP),    -- JNJ
    (8, 28.50, CURRENT_TIMESTAMP),     -- PFE
    (9, 108.70, CURRENT_TIMESTAMP),    -- XOM
    (10, 78.90, CURRENT_TIMESTAMP),    -- NEE
    (11, 510.25, CURRENT_TIMESTAMP),   -- SPY
    (12, 99.80, CURRENT_TIMESTAMP);    -- AGG

-- Insert some historical prices
INSERT INTO prices (asset_id, price, as_of) VALUES
    (1, 172.30, CURRENT_TIMESTAMP - INTERVAL '7 days'),
    (1, 169.80, CURRENT_TIMESTAMP - INTERVAL '14 days'),
    (2, 408.50, CURRENT_TIMESTAMP - INTERVAL '7 days'),
    (2, 395.00, CURRENT_TIMESTAMP - INTERVAL '14 days'),
    (5, 190.20, CURRENT_TIMESTAMP - INTERVAL '7 days'),
    (5, 185.00, CURRENT_TIMESTAMP - INTERVAL '14 days');

-- 3. USEFUL VIEWS

-- View: Latest price per asset
CREATE OR REPLACE VIEW latest_prices AS
SELECT DISTINCT ON (asset_id)
    asset_id, price, as_of
FROM prices
ORDER BY asset_id, as_of DESC;

-- View: Portfolio holdings with current values
CREATE OR REPLACE VIEW portfolio_holdings AS
SELECT
    p.portfolio_id,
    pf.name AS portfolio_name,
    a.symbol,
    a.name AS asset_name,
    a.sector,
    a.asset_type,
    p.quantity,
    p.avg_cost,
    lp.price AS current_price,
    (p.quantity * lp.price) AS market_value,
    (p.quantity * (lp.price - p.avg_cost)) AS unrealized_pnl,
    ROUND(((lp.price - p.avg_cost) / p.avg_cost) * 100, 2) AS pnl_pct
FROM positions p
JOIN portfolios pf ON p.portfolio_id = pf.portfolio_id
JOIN assets a ON p.asset_id = a.asset_id
JOIN latest_prices lp ON a.asset_id = lp.asset_id;
