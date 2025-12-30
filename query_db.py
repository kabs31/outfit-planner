"""
Direct SQLite query to check products
"""
import sqlite3

conn = sqlite3.connect('backend/outfit_planner.db')
cursor = conn.cursor()

# Get all products
cursor.execute("SELECT id, name, category, price, brand FROM products")
products = cursor.fetchall()

print(f"Total products: {len(products)}\n")
print("="*100)

for p in products:
    print(f"ID: {p[0]}, Name: {p[1][:50]}, Category: {p[2]}, Price: {p[3]}, Brand: {p[4]}")
    
conn.close()
