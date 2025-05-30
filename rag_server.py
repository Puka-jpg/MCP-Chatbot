import os
import pickle
import json
import numpy as np
import voyageai
from mcp.server.fastmcp import FastMCP
import glob
from pathlib import Path
from dotenv import load_dotenv

# Initialize MCP server
mcp = FastMCP("rag_neuralflow")
load_dotenv()

class VectorDB:
    def __init__(self, name, api_key=None):
        if api_key is None:
            api_key = os.getenv("VOYAGE_API_KEY")
        self.client = voyageai.Client(api_key=api_key)
        self.name = name
        self.embeddings = []
        self.metadata = []
        self.query_cache = {}
        self.db_path = f"./data/{name}/vector_db.pkl"

    def load_data(self, data):
        if self.embeddings and self.metadata:
            print("Vector database is already loaded. Skipping data loading.")
            return
        if os.path.exists(self.db_path):
            print("Loading vector database from disk.")
            self.load_db()
            return

        texts = [f"Heading: {item['chunk_heading']}\n\nChunk Text: {item['text']}" for item in data]
        self._embed_and_store(texts, data)
        self.save_db()
        print("Vector database loaded and saved.")

    def _embed_and_store(self, texts, data):
        batch_size = 128
        result = [
            self.client.embed(
                texts[i : i + batch_size],
                model="voyage-2"
            ).embeddings
            for i in range(0, len(texts), batch_size)
        ]
        self.embeddings = [embedding for batch in result for embedding in batch]
        self.metadata = data

    def search(self, query, k=3, similarity_threshold=0.70):
        if query in self.query_cache:
            query_embedding = self.query_cache[query]
        else:
            query_embedding = self.client.embed([query], model="voyage-2").embeddings[0]
            self.query_cache[query] = query_embedding

        if not self.embeddings:
            raise ValueError("No data loaded in the vector database.")

        similarities = np.dot(self.embeddings, query_embedding)
        top_indices = np.argsort(similarities)[::-1]
        top_examples = []
        
        for idx in top_indices:
            if similarities[idx] >= similarity_threshold:
                example = {
                    "metadata": self.metadata[idx],
                    "similarity": similarities[idx],
                }
                top_examples.append(example)
                
                if len(top_examples) >= k:
                    break
        
        return top_examples

    def save_db(self):
        data = {
            "embeddings": self.embeddings,
            "metadata": self.metadata,
            "query_cache": json.dumps(self.query_cache),
        }
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "wb") as file:
            pickle.dump(data, file)

    def load_db(self):
        if not os.path.exists(self.db_path):
            raise ValueError("Vector database file not found.")
        with open(self.db_path, "rb") as file:
            data = pickle.load(file)
        self.embeddings = data["embeddings"]
        self.metadata = data["metadata"]
        self.query_cache = json.loads(data["query_cache"])

# Initialize vector database
db = VectorDB("neuralflow_docs")

def load_and_process_documents():
    """Load txt files and create chunks for embedding"""
    docs_data = []
    
    # Process all  files in neuralflow
    md_files = glob.glob("./neuralflow_docs/**/*.txt", recursive=True)
    
    for file_path in md_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic chunking - split by sections/paragraphs
            sections = content.split('\n\n')
            file_name = Path(file_path).stem
            
            for i, section in enumerate(sections):
                if section.strip():  # Skip empty sections
                    docs_data.append({
                        'text': section.strip(),
                        'chunk_heading': f"{file_name}_section_{i}",
                        'source_file': file_path,
                        'chunk_id': f"{file_name}_{i}"
                    })
                    
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return docs_data

# Load documents on server startup
print("Loading and processing documents...")
documents = load_and_process_documents()
db.load_data(documents)
print(f"Loaded {len(documents)} document chunks into vector database")

@mcp.tool()
def semantic_search(query: str, k: int = 5) -> str:
    """Search for relevant document chunks using semantic similarity"""
    try:
        results = db.search(query, k=k)
        
        if not results:
            return "No relevant documents found for your query."
        
        context = ""
        for result in results:
            chunk = result['metadata']
            similarity = result['similarity']
            context += f"\n--- Source: {chunk['source_file']} (Similarity: {similarity:.3f}) ---\n"
            context += f"{chunk['text']}\n"
        
        return context
        
    except Exception as e:
        return f"Error during search: {str(e)}"

if __name__ == "__main__":
    print("Starting NeruralFlow RAG MCP Server...")
    mcp.run(transport='stdio')