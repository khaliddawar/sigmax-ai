import os
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import httpx

logger = logging.getLogger("bpt-embedding-service")

class EmbeddingService:
    """Service for generating vector embeddings from text using various LLM API providers"""
    
    def __init__(self):
        """Initialize the embedding service with API keys from environment variables"""
        self.api_key_openai = os.getenv("OPENAI_API_KEY")
        self.api_key_azure = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_key_cohere = os.getenv("COHERE_API_KEY")
        
        # Configuration
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
        self.embedding_dimension = self._get_embedding_dimension(self.embedding_model)
        self.batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "20"))  # Number of texts per API call
        self.use_mock = os.getenv("USE_MOCK_EMBEDDINGS", "false").lower() == "true"
        self.provider = self._determine_provider()
        
        # Azure specific settings
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_api_version = os.getenv("AZURE_API_VERSION", "2023-05-15")
        
        # HTTP client for API calls - will be properly managed
        self._http_client = None
        
        # Log configuration
        if self.use_mock:
            logger.info("Using mock embeddings (random vectors)")
        else:
            logger.info(f"Embedding service initialized with provider: {self.provider}, model: {self.embedding_model}")
    
    @property
    def http_client(self):
        """Lazy initialization of HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client
    
    async def close(self):
        """Properly close the HTTP client to prevent connection leaks"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    def _determine_provider(self) -> str:
        """Determine which embedding provider to use based on available API keys"""
        if self.api_key_openai:
            return "openai"
        elif self.api_key_azure and self.azure_endpoint:
            return "azure"
        elif self.api_key_cohere:
            return "cohere"
        else:
            logger.warning("No embedding provider API keys available. Using mock embeddings.")
            self.use_mock = True
            return "mock"
    
    def _get_embedding_dimension(self, model_name: str) -> int:
        """Get the output dimension for a given embedding model"""
        dimensions = {
            # OpenAI models
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            # Cohere models
            "embed-english-v3.0": 1024,
            "embed-multilingual-v3.0": 1024,
            # Default fallback
            "default": 1536
        }
        
        return dimensions.get(model_name, dimensions["default"])
    
    async def get_embeddings(self, 
                           texts: List[str], 
                           retry_count: int = 3, 
                           retry_delay: float = 1.0) -> Optional[List[List[float]]]:
        """
        Generate embeddings for a list of text chunks using the configured provider
        Returns a list of embedding vectors or None if unsuccessful
        """
        if not texts:
            logger.warning("Cannot generate embeddings: No texts provided")
            return None
            
        # When mock mode is enabled, generate random embeddings for testing
        if self.use_mock:
            return self._generate_mock_embeddings(texts)
        
        # Process in batches to avoid rate limits
        all_embeddings = []
        total_batches = (len(texts) - 1) // self.batch_size + 1
        
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i+self.batch_size]
            batch_num = i // self.batch_size + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} with {len(batch_texts)} texts")
            
            # Try primary provider with retries
            embedding_result = await self._get_embeddings_with_retry(
                batch_texts, self.provider, retry_count, retry_delay)
            
            if embedding_result:
                logger.info(f"Successfully generated embeddings for batch {batch_num} using {self.provider}")
                all_embeddings.extend(embedding_result)
            else:
                # Try fallback providers if primary failed
                fallback_result = await self._try_fallback_providers(batch_texts, retry_count, retry_delay)
                
                if fallback_result:
                    logger.info(f"Used fallback provider for batch {batch_num}")
                    all_embeddings.extend(fallback_result)
                else:
                    # All providers failed, use mock embeddings as last resort
                    logger.warning(f"All providers failed for batch {batch_num}. Using mock embeddings.")
                    mock_embeddings = self._generate_mock_embeddings(batch_texts)
                    all_embeddings.extend(mock_embeddings)
        
        return all_embeddings
    
    async def _get_embeddings_with_retry(self, 
                                       texts: List[str], 
                                       provider: str,
                                       retry_count: int, 
                                       retry_delay: float) -> Optional[List[List[float]]]:
        """Try to get embeddings with retry logic"""
        for attempt in range(retry_count):
            try:
                # Call appropriate provider
                if provider == "openai":
                    return await self._get_openai_embeddings(texts)
                elif provider == "azure":
                    return await self._get_azure_embeddings(texts)
                elif provider == "cohere":
                    return await self._get_cohere_embeddings(texts)
                else:
                    logger.error(f"Unknown provider: {provider}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error generating embeddings with {provider} (attempt {attempt+1}/{retry_count}): {str(e)}")
                
                if attempt < retry_count - 1:
                    # Exponential backoff with jitter
                    sleep_time = retry_delay * (2 ** attempt) * (0.5 + 0.5 * np.random.random())
                    logger.info(f"Retrying after {sleep_time:.2f} seconds...")
                    await asyncio.sleep(sleep_time)
        
        return None
    
    async def _try_fallback_providers(self, 
                                    texts: List[str],
                                    retry_count: int,
                                    retry_delay: float) -> Optional[List[List[float]]]:
        """Try alternative providers if the primary one fails"""
        # List of providers to try, excluding the primary one
        fallback_providers = []
        
        if self.provider != "openai" and self.api_key_openai:
            fallback_providers.append("openai")
            
        if self.provider != "azure" and self.api_key_azure and self.azure_endpoint:
            fallback_providers.append("azure")
            
        if self.provider != "cohere" and self.api_key_cohere:
            fallback_providers.append("cohere")
        
        for provider in fallback_providers:
            logger.info(f"Trying fallback provider: {provider}")
            result = await self._get_embeddings_with_retry(texts, provider, retry_count, retry_delay)
            if result:
                return result
        
        return None
    
    async def _get_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings using OpenAI API"""
        if not self.api_key_openai:
            raise ValueError("OpenAI API key not set")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key_openai}"
        }
        
        payload = {
            "model": self.embedding_model,
            "input": texts
        }
        
        response = await self.http_client.post(
            "https://api.openai.com/v1/embeddings",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code}, {response.text}")
        
        result = response.json()
        return [item["embedding"] for item in result["data"]]
    
    async def _get_azure_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings using Azure OpenAI API"""
        if not self.api_key_azure or not self.azure_endpoint:
            raise ValueError("Azure OpenAI API key or endpoint not set")
        
        # Extract deployment name from model name or use directly
        deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", self.embedding_model)
        
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key_azure
        }
        
        payload = {
            "input": texts
        }
        
        response = await self.http_client.post(
            f"{self.azure_endpoint}/openai/deployments/{deployment_name}/embeddings?api-version={self.azure_api_version}",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Azure API error: {response.status_code}, {response.text}")
        
        result = response.json()
        return [item["embedding"] for item in result["data"]]
    
    async def _get_cohere_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings using Cohere API"""
        if not self.api_key_cohere:
            raise ValueError("Cohere API key not set")
        
        # Map OpenAI model names to Cohere models if necessary
        cohere_model = "embed-english-v3.0"  # Default Cohere model
        
        headers = {
            "Authorization": f"Bearer {self.api_key_cohere}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": cohere_model,
            "texts": texts,
            "truncate": "END"
        }
        
        response = await self.http_client.post(
            "https://api.cohere.ai/v1/embed",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Cohere API error: {response.status_code}, {response.text}")
        
        result = response.json()
        return result["embeddings"]
    
    def _generate_mock_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate random embeddings for testing purposes"""
        # For each text, generate a random vector with proper dimensionality
        # Use the hash of the text to seed the random generator for consistency
        mock_embeddings = []
        
        for text in texts:
            # Create a seed from the text hash
            text_hash = hash(text) % 10000
            # Seed random generator for consistent embeddings for the same text
            np.random.seed(text_hash)
            # Generate random vector and normalize it
            vector = np.random.normal(0, 1, self.embedding_dimension)
            normalized = vector / np.linalg.norm(vector)
            mock_embeddings.append(normalized.tolist())
        
        return mock_embeddings
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text"""
        embeddings = await self.get_embeddings([text])
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        return None
    
    async def generate_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        Generate embeddings for a list of text chunks - alias for get_embeddings
        This method exists for compatibility with services that call generate_embeddings
        """
        return await self.get_embeddings(texts)
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        # Convert to numpy arrays for efficient calculation
        a = np.array(embedding1)
        b = np.array(embedding2)
        
        # Calculate cosine similarity: dot product / (norm(a) * norm(b))
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """Calculate the average embedding from a list of embeddings"""
        if not embeddings:
            return [0] * self.embedding_dimension
            
        # Convert to numpy array and take mean along axis 0
        avg_embedding = np.mean(np.array(embeddings), axis=0).tolist()
        return avg_embedding
        
    async def most_similar(self, 
                         query_embedding: List[float], 
                         candidate_embeddings: List[List[float]],
                         top_k: int = 5) -> List[Tuple[int, float]]:
        """
        Find the most similar embeddings to a query embedding
        Returns a list of (index, similarity) tuples
        """
        if not candidate_embeddings:
            return []
        
        # Calculate similarities efficiently using numpy
        query_array = np.array(query_embedding)
        candidates_array = np.array(candidate_embeddings)
        
        # Normalize vectors for cosine similarity
        query_norm = query_array / np.linalg.norm(query_array)
        candidates_norm = candidates_array / np.linalg.norm(candidates_array, axis=1, keepdims=True)
        
        # Calculate dot product (cosine similarity for normalized vectors)
        similarities = np.dot(candidates_norm, query_norm)
        
        # Get indices of top-k similarities
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Return (index, similarity) tuples
        results = [(int(idx), float(similarities[idx])) for idx in top_indices]
        return results 
    
    async def get_embeddings_streaming(self, 
                                    texts: List[str],
                                    storage_callback = None,
                                    batch_size: int = None,
                                    retry_count: int = 3, 
                                    retry_delay: float = 1.0) -> Optional[List[List[float]]]:
        """
        Generate embeddings in streaming mode - processes and optionally stores in smaller batches
        to reduce memory pressure for large transcripts.
        
        Args:
            texts: List of text chunks to embed
            storage_callback: Optional async function(batch_embeddings, batch_start_idx) to store embeddings immediately
            batch_size: Override default batch size for memory optimization
            retry_count: Number of retries per batch
            retry_delay: Base delay between retries
            
        Returns:
            List of embeddings if no storage_callback, otherwise None (embeddings stored via callback)
        """
        if not texts:
            logger.warning("Cannot generate embeddings: No texts provided")
            return None
            
        # Use smaller batch size for streaming to reduce memory pressure
        effective_batch_size = batch_size or max(5, self.batch_size // 4)
        
        # When mock mode is enabled, generate random embeddings for testing
        if self.use_mock:
            if storage_callback:
                # Process in small batches for streaming
                for i in range(0, len(texts), effective_batch_size):
                    batch_texts = texts[i:i+effective_batch_size]
                    batch_embeddings = self._generate_mock_embeddings(batch_texts)
                    await storage_callback(batch_embeddings, i)
                return None
            else:
                return self._generate_mock_embeddings(texts)
        
        # Streaming mode - process and store in small batches
        if storage_callback:
            total_batches = (len(texts) - 1) // effective_batch_size + 1
            logger.info(f"Streaming embeddings in {total_batches} batches of {effective_batch_size}")
            
            for i in range(0, len(texts), effective_batch_size):
                batch_texts = texts[i:i+effective_batch_size]
                batch_num = i // effective_batch_size + 1
                
                logger.info(f"Processing streaming batch {batch_num}/{total_batches} with {len(batch_texts)} texts")
                
                # Generate embeddings for this batch
                batch_embeddings = await self._get_embeddings_with_retry(
                    batch_texts, self.provider, retry_count, retry_delay)
                
                if batch_embeddings:
                    logger.info(f"Successfully generated embeddings for streaming batch {batch_num}")
                    # Store immediately to free memory
                    await storage_callback(batch_embeddings, i)
                else:
                    # Try fallback providers
                    fallback_result = await self._try_fallback_providers(batch_texts, retry_count, retry_delay)
                    
                    if fallback_result:
                        logger.info(f"Used fallback provider for streaming batch {batch_num}")
                        await storage_callback(fallback_result, i)
                    else:
                        # Use mock embeddings as last resort
                        logger.warning(f"All providers failed for streaming batch {batch_num}. Using mock embeddings.")
                        mock_embeddings = self._generate_mock_embeddings(batch_texts)
                        await storage_callback(mock_embeddings, i)
            
            return None  # Embeddings stored via callback
        else:
            # Non-streaming mode - use original implementation
            return await self.get_embeddings(texts, retry_count, retry_delay) 