"""2000 синтетических заказов, seed 20261027, в SQLite. Детерминированно: одинаковая база на любой машине."""
import random, sqlite3, sys
def build(path):
    rnd = random.Random(20261027)
    con = sqlite3.connect(path); con.execute("DROP TABLE IF EXISTS orders")
    con.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, region TEXT, customer_type TEXT, is_wholesale INTEGER, is_vip INTEGER, qty INTEGER, price_cents INTEGER, coupon INTEGER)")
    for i in range(1, 2001):
        ct = rnd.choice(["retail", "retail", "wholesale", "vip"])
        con.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)", (i, rnd.choice(["north", "south", "east", "west"]), ct, int(ct == "wholesale"), int(ct == "vip"), rnd.randint(1, 50), rnd.randint(100, 50000), int(rnd.random() < 0.2)))
    con.commit(); con.close()
if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "orders.db")
