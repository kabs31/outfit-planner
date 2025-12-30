"""
Check product names to understand categorization
"""
import sqlite3

conn = sqlite3.connect('backend/outfit_planner.db')
cursor = conn.cursor()

cursor.execute("SELECT id, name, category FROM products ORDER BY category, id")
products = cursor.fetchall()

print("Products in database:\n")
print("="*120)

tops = []
bottoms = []

for p in products:
    name_truncated = p[1][:70] if len(p[1]) > 70 else p[1]
    print(f"ID {p[0]:<3} | {p[2]:<8} | {name_truncated}")
    
    if p[2] == 'top':
        tops.append(p)
    elif p[2] == 'bottom':
        bottoms.append(p)

print(f"\n{'='*120}")
print(f"✅ Tops: {len(tops)}")
print(f"✅ Bottoms: {len(bottoms)}")
print(f"\n⚠️  PROBLEM: We need BOTH tops and bottoms to create outfit combinations!")
print(f"   The outfit generation requires at least 1 top AND 1 bottom.")

conn.close()
