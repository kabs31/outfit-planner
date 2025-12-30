"""
Check what products FakeStoreAPI returns and their categories
"""
import sqlite3

conn = sqlite3.connect('backend/outfit_planner.db')
cursor = conn.cursor()

cursor.execute("SELECT id, name, category FROM products")
products = cursor.fetchall()

print("Products from FakeStoreAPI:\n")
print("="*100)

tops = []
bottoms = []

for p in products:
    print(f"ID: {p[0]:<5} | Category: {p[1]:<10} | Name: {p[2]}")
    if p[1] == 'top':
        tops.append(p)
    else:
        bottoms.append(p)

print(f"\n{'='*100}")
print(f"Summary: {len(tops)} tops, {len(bottoms)} bottoms")
print(f"\n⚠️  ISSUE: Need both tops AND bottoms to create outfit combinations!")

conn.close()
