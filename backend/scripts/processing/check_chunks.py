import json

with open('chunks_with_embeddings.json', 'r') as f:
    data = json.load(f)

print(f"Total chunks: {len(data)}")
print(f"Chunk 2 text preview: {data[1]['text'][:100]}...")
print(f"Chunk 2 embedding length: {len(data[1]['embedding'])}")
print(f"Chunk 2 index: {data[1]['chunk_index']}") 