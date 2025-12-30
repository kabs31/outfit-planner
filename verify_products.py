"""
Verify synced products in database
"""
import sqlite3

conn = sqlite3.connect('backend/outfit_planner.db')
cursor = conn.cursor()

# Get all products with category count
cursor.execute("SELECT category, COUNT(*) FROM products GROUP BY category")
category_counts = cursor.fetchall()

print("📊 Product Categories:")
print("="*60)
for cat, count in category_counts:
    print(f"  {cat}: {count} products")

print(f"\n{'='*60}")

# Show sample products from each category
print("\n📦 Sample Products:\n")

cursor.execute("SELECT id, name, category, price FROM products WHERE category='top' LIMIT 5")
tops = cursor.fetchall()
print("TOPS:")
for p in tops:
    print(f"  • {p[1]} - ₹{p[3]}")

print("\nBOTTOMS:")
cursor.execute("SELECT id, name, category, price FROM products WHERE category='bottom' LIMIT 5")
bottoms = cursor.fetchall()
for p in bottoms:
    print(f"  • {p[1]} - ₹{p[3]}")

# Total count
cursor.execute("SELECT COUNT(*) FROM products")
total = cursor.fetchone()[0]
print(f"\n{'='*60}")
print(f"✅ Total products in database: {total}")
print(f"{'='*60}\n")

conn.close()
