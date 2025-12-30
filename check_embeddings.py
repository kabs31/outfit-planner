"""
Check if products have embeddings
"""
import sqlite3

conn = sqlite3.connect('backend/outfit_planner.db')
cursor = conn.cursor()

# Check embedding column
cursor.execute("SELECT id, name, category, embedding FROM products")
products = cursor.fetchall()

print(f"Total products: {len(products)}\n")

products_with_embeddings = 0
products_without_embeddings = 0

for p in products:
    has_embedding = p[3] is not None
    if has_embedding:
        products_with_embeddings += 1
    else:
        products_without_embeddings += 1
    
    print(f"ID: {p[0]}, Category: {p[2]}, Has Embedding: {has_embedding}")

print(f"\n✅ Products WITH embeddings: {products_with_embeddings}")
print(f"❌ Products WITHOUT embeddings: {products_without_embeddings}")

conn.close()
