import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "dbname": "portfolio_risk",
    "user": "postgres",
    "password": "postgres",
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def show_portfolios():
    """List available portfolios."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT portfolio_id, name, owner FROM portfolios ORDER BY portfolio_id;")
    rows = cur.fetchall()
    print(f"\n  Available Portfolios:")
    print(f"  {'-'*40}")
    for r in rows:
        print(f"    [{r['portfolio_id']}] {r['name']} (Owner: {r['owner']})")
    cur.close()
    conn.close()
    return rows


def portfolio_snapshot():
    """
    Feature 1: Portfolio Risk Snapshot
    Uses REPEATABLE READ so all queries see the same consistent data.
    """
    show_portfolios()
    while True:
        try:
            portfolio_id = int(input("\n Enter portfolio ID: "))
            break
        except ValueError:
            print("  Please enter a valid number.")
    conn = get_connection()
    conn.set_session(isolation_level="REPEATABLE READ", readonly=True)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT txid_current_snapshot();")
    snapshot = cur.fetchone()["txid_current_snapshot"]
    cur.execute("SELECT txid_current();")
    txid = cur.fetchone()["txid_current"]

    print(f"\n{'='*60}")
    print(f"  PORTFOLIO RISK SNAPSHOT")
    print(f"{'='*60}")
    print(f"  Transaction ID: {txid}")
    print(f"  Snapshot:        {snapshot}")
    print(f"  Isolation Level: REPEATABLE READ")
    print(f"\n  All queries below see the exact same snapshot.")
    print(f"  Even if another session updates prices right now,")
    print(f"  this transaction would still see the original data.")

    cur.execute("""
        SELECT portfolio_name,
               COUNT(*) AS num_positions,
               SUM(market_value) AS total_value,
               SUM(unrealized_pnl) AS total_pnl,
               SUM(quantity * avg_cost) AS cost_basis
        FROM portfolio_holdings
        WHERE portfolio_id = %s
        GROUP BY portfolio_name;
    """, (portfolio_id,))
    s = cur.fetchone()
    if not s:
        print(f"\n  Portfolio not found.")
        conn.commit()
        cur.close()
        conn.close()
        return

    pnl_pct = (s['total_pnl'] / s['cost_basis']) * 100
    print(f"\n  Portfolio:      {s['portfolio_name']}")
    print(f"  Positions:      {s['num_positions']}")
    print(f"  Cost Basis:     ${s['cost_basis']:>12,.2f}")
    print(f"  Total Value:    ${s['total_value']:>12,.2f}")
    print(f"  Unrealized P&L: ${s['total_pnl']:>12,.2f} ({pnl_pct:+.2f}%)")

    cur.execute("""
        SELECT sector,
               SUM(market_value) AS sector_value,
               ROUND(SUM(market_value) /
                     SUM(SUM(market_value)) OVER () * 100, 2) AS sector_pct
        FROM portfolio_holdings
        WHERE portfolio_id = %s
        GROUP BY sector
        ORDER BY sector_value DESC;
    """, (portfolio_id,))
    sectors = cur.fetchall()
    print(f"\n  {'Sector':<15} {'Value':>12} {'Weight':>8}")
    print(f"  {'-'*37}")
    for sec in sectors:
        print(f"  {sec['sector']:<15} ${sec['sector_value']:>10,.2f} {sec['sector_pct']:>6}%")

    cur.execute("""
        SELECT symbol, asset_name, sector, quantity, avg_cost,
               current_price, market_value, unrealized_pnl, pnl_pct
        FROM portfolio_holdings
        WHERE portfolio_id = %s
        ORDER BY market_value DESC;
    """, (portfolio_id,))
    holdings = cur.fetchall()
    print(f"\n  {'Symbol':<7} {'Sector':<13} {'Qty':>6} {'Price':>9} {'Value':>12} {'P&L':>10} {'P&L%':>7}")
    print(f"  {'-'*67}")
    for h in holdings:
        sign = "+" if h['pnl_pct'] >= 0 else ""
        print(f"  {h['symbol']:<7} {h['sector']:<13} {h['quantity']:>6.0f} "
              f"${h['current_price']:>7,.2f} ${h['market_value']:>10,.2f} "
              f"${h['unrealized_pnl']:>8,.2f} {sign}{h['pnl_pct']}%")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n  Transaction committed. Snapshot released.")


def whatif_simulation():
    """
    Feature 2: What-If Scenario Simulation
    Interactive step-by-step with pauses so you control the pacing.
    """
    show_portfolios()
    while True:
        try:
            portfolio_id = int(input("\n Enter portfolio ID: "))
            break
        except ValueError:
            print(" Please enter a valid number.")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT DISTINCT sector FROM assets ORDER BY sector;")
    sectors = [r['sector'] for r in cur.fetchall()]

    print(f"\n  Choose a scenario:")
    print(f"    [1] Tech Crash (Technology -20%)")
    print(f"    [2] Energy Crisis (Energy -25%)")


    choice = input("\n  Enter choice (1-2): ")

    if choice == "1":
        scenario_name = "Tech Crash"
        adjustments = {"Technology": -20}
    elif choice == "2":
        scenario_name = "Energy Crisis"
        adjustments = {"Energy": -25}

    else:
        print("  Invalid choice.")
        cur.close()
        conn.close()
        return

    print(f"\n{'='*60}")
    print(f"  WHAT-IF SIMULATION: {scenario_name}")
    print(f"{'='*60}")

    #  Step 1 
    input("\n  >> Press Enter to BEGIN transaction and read original value...")

    cur.execute("""
        SELECT SUM(market_value) AS total_value,
               SUM(unrealized_pnl) AS total_pnl
        FROM portfolio_holdings WHERE portfolio_id = %s;
    """, (portfolio_id,))
    before = cur.fetchone()

    print(f"\n  Original Value: ${before['total_value']:,.2f}")
    print(f"  Original P&L:   ${before['total_pnl']:,.2f}")

    #  Step 2 
    input("\n  >> Press Enter to apply price adjustments (UPDATE)...")

    print(f"\n  PostgreSQL creates NEW row versions. Old rows are NOT overwritten.")
    for sector, pct_change in adjustments.items():
        multiplier = 1 + (pct_change / 100.0)
        cur.execute("""
            UPDATE prices SET price = price * %s
            WHERE asset_id IN (SELECT asset_id FROM assets WHERE sector = %s)
              AND (asset_id, as_of) IN (
                  SELECT asset_id, MAX(as_of) FROM prices GROUP BY asset_id
              );
        """, (multiplier, sector))
        print(f"    {sector}: {pct_change:+}% applied ({cur.rowcount} rows)")

    # Step 3 
    input("\n  >> Press Enter to recalculate portfolio with simulated prices...")

    cur.execute("""
        SELECT SUM(market_value) AS total_value,
               SUM(unrealized_pnl) AS total_pnl
        FROM portfolio_holdings WHERE portfolio_id = %s;
    """, (portfolio_id,))
    after = cur.fetchone()
    change = after['total_value'] - before['total_value']
    change_pct = (change / before['total_value']) * 100

    print(f"\n  Simulated Value: ${after['total_value']:,.2f}")
    print(f"  Simulated P&L:   ${after['total_pnl']:,.2f}")
    print(f"  Impact:           ${change:,.2f} ({change_pct:+.2f}%)")

    # Step 4 
    input("\n  >> Press Enter to ROLLBACK the transaction...")

    conn.rollback()
    print(f"\n  >>> ROLLBACK complete <<<")
    print(f"  The temporary price changes have been discarded.")
    print(f"  Original data is restored.")

    # Step 5 
    input("\n  >> Press Enter to verify data is unchanged...")

    cur.execute("""
        SELECT SUM(market_value) AS total_value
        FROM portfolio_holdings WHERE portfolio_id = %s;
    """, (portfolio_id,))
    verify = cur.fetchone()["total_value"]
    match = verify == before['total_value']

    print(f"\n  Current Value:    ${verify:,.2f}")
    print(f"  Original Value:   ${before['total_value']:,.2f}")
    print(f"  Match: {match}")
    if match:
        print(f"\n  Verified: no data was permanently changed.")
    print(f"{'='*60}")

    cur.close()
    conn.close()


def concurrent_demo():
    """
    Feature 3: Demonstrate that uncommitted changes are invisible
    to other connections. This is MVCC in action.
    """
    print(f"  MVCC CONCURRENT ACCESS DEMO")
    print(f"  Two connections, same database, different views")

    conn_a = get_connection()
    conn_b = get_connection()
    cur_a = conn_a.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur_b = conn_b.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Step 1
    input("\n  >> Press Enter to read AAPL price from both connections...")

    cur_a.execute("""
        SELECT a.symbol, p.price
        FROM prices p JOIN assets a ON p.asset_id = a.asset_id
        WHERE a.symbol = 'AAPL'
        ORDER BY p.as_of DESC LIMIT 1;
    """)
    price_a = cur_a.fetchone()

    cur_b.execute("""
        SELECT a.symbol, p.price
        FROM prices p JOIN assets a ON p.asset_id = a.asset_id
        WHERE a.symbol = 'AAPL'
        ORDER BY p.as_of DESC LIMIT 1;
    """)
    price_b = cur_b.fetchone()

    print(f"\n  Connection A sees AAPL: ${price_a['price']:,.2f}")
    print(f"  Connection B sees AAPL: ${price_b['price']:,.2f}")
    print(f"  Both see the same price.")

    # Step 2
    input("\n  >> Press Enter to UPDATE AAPL to $999.99 on Connection A (no commit)...")

    cur_a.execute("""
        UPDATE prices SET price = 999.99
        WHERE asset_id = (SELECT asset_id FROM assets WHERE symbol = 'AAPL')
          AND as_of = (SELECT MAX(as_of) FROM prices
                       WHERE asset_id = (SELECT asset_id FROM assets WHERE symbol = 'AAPL'));
    """)
    print(f"\n  Connection A updated AAPL to $999.99 (NOT committed)")

    # Step 3
    input("\n  >> Press Enter to read AAPL from BOTH connections...")

    cur_a.execute("""
        SELECT a.symbol, p.price
        FROM prices p JOIN assets a ON p.asset_id = a.asset_id
        WHERE a.symbol = 'AAPL'
        ORDER BY p.as_of DESC LIMIT 1;
    """)
    price_a2 = cur_a.fetchone()

    cur_b.execute("""
        SELECT a.symbol, p.price
        FROM prices p JOIN assets a ON p.asset_id = a.asset_id
        WHERE a.symbol = 'AAPL'
        ORDER BY p.as_of DESC LIMIT 1;
    """)
    price_b2 = cur_b.fetchone()

    print(f"\n  Connection A sees AAPL: ${price_a2['price']:,.2f}  (sees its own update)")
    print(f"  Connection B sees AAPL: ${price_b2['price']:,.2f}  (still sees original!)")
    print(f"\n  Connection B cannot see the change because A hasn't committed.")
    print(f"  PostgreSQL kept the old row version visible to B.")

    # Step 4
    input("\n  >> Press Enter to ROLLBACK Connection A's change...")

    conn_a.rollback()
    print(f"\n  Connection A rolled back.")

    cur_a.execute("""
        SELECT a.symbol, p.price
        FROM prices p JOIN assets a ON p.asset_id = a.asset_id
        WHERE a.symbol = 'AAPL'
        ORDER BY p.as_of DESC LIMIT 1;
    """)
    price_a3 = cur_a.fetchone()

    cur_b.execute("""
        SELECT a.symbol, p.price
        FROM prices p JOIN assets a ON p.asset_id = a.asset_id
        WHERE a.symbol = 'AAPL'
        ORDER BY p.as_of DESC LIMIT 1;
    """)
    price_b3 = cur_b.fetchone()

    print(f"  Connection A sees AAPL: ${price_a3['price']:,.2f}  (back to original)")
    print(f"  Connection B sees AAPL: ${price_b3['price']:,.2f}  (back to original)")
    print(f"\n  Original data is fully restored.")

    cur_a.close()
    cur_b.close()
    conn_a.close()
    conn_b.close()


def main():
    print(f"  PORTFOLIO RISK SNAPSHOT & WHAT-IF SIMULATION")
    print(f"  DSCI 551 Project - PostgreSQL MVCC Demo")
    print(f"  Author: David Kim")

    while True:
        print(f"\n  Main Menu:")
        print(f"    [1] Portfolio Risk Snapshot")
        print(f"    [2] What-If Scenario Simulation")
        print(f"    [3] MVCC Concurrent Access Demo")
        print(f"    [4] Exit")

        choice = input("\n  Enter choice (1-4): ")

        if choice == "1":
            portfolio_snapshot()
        elif choice == "2":
            whatif_simulation()
        elif choice == "3":
            concurrent_demo()
        elif choice == "4":
            print("\n  Goodbye!\n")
            break
        else:
            print("  Invalid choice. Try again.")



if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n  ERROR: {e}")
        input("\n  Press Enter to close...")
        