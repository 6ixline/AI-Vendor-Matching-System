"""Reset Qdrant database - delete all data"""

from qdrant_client import QdrantClient

def reset_database():
    print("\n" + "="*70)
    print("RESETTING QDRANT DATABASE")
    print("="*70 + "\n")
    
    client = QdrantClient(host="localhost", port=6333)
    collections = ["vendors", "tenders", "feedback"]
    
    for collection in collections:
        try:
            client.delete_collection(collection)
            print(f"Deleted collection: {collection}")
        except Exception as e:
            print(f"Collection '{collection}' doesn't exist or error: {e}")
    
    print("\n" + "="*70)
    print("DATABASE RESET COMPLETE!")
    print("="*70)

if __name__ == "__main__":
    reset_database()
