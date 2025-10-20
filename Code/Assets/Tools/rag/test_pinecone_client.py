import os
import time
import unittest
from .pinecone_client import RAG

class TestPineconeRAG(unittest.TestCase):
    _shared_rag = None

    @classmethod
    def setUpClass(cls):
        # Ensure we have an API key
        if not os.getenv("PINECONE_API_KEY"):
            raise ValueError("PINECONE_API_KEY environment variable not set")
        if cls._shared_rag is None:
            cls._shared_rag = RAG(collection="test-collection")
        cls.rag = cls._shared_rag
        
    def test_basic_indexing_and_retrieval(self):
        # Test data
        ids = ["1", "2", "3"]
        texts = [
            "Apple reported strong earnings in Q4 2024",
            "Tesla's new electric vehicle sales increased",
            "Microsoft announced a new AI product"
        ]
        metadata = [{"source": "news"} for _ in range(3)]
        
        # Index the documents
        self.rag.index(ids, texts, metadata)
        
        # Wait for indexing to complete
        time.sleep(5)  # Give Pinecone time to index

        # Test retrieval
        results = self.rag.retrieve("What did Apple report?", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("Apple", results[0])
        
        results = self.rag.retrieve("Tell me about electric vehicles", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("Tesla", results[0])

    def test_empty_queries(self):
        results = self.rag.retrieve("", top_k=3)
        self.assertEqual(len(results), 0)

    def test_batch_indexing(self):
        # Test with more than 100 documents to test batching
        ids = [str(i) for i in range(120)]
        texts = [f"Test document {i}" for i in range(120)]
        metadata = [{"doc_id": i} for i in range(120)]
        
        # This should work without errors despite being more than batch_size
        self.rag.index(ids, texts, metadata)
        
        # Verify we can retrieve one of the later documents
        results = self.rag.retrieve("Test document 119", top_k=1)
        self.assertTrue(len(results) > 0)
        self.assertIn("119", results[0])

if __name__ == '__main__':
    unittest.main()