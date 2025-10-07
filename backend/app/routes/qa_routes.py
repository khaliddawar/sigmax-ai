from fastapi import APIRouter, Request, HTTPException
import logging
import json
import traceback
import re
from typing import Optional, Dict, Any, List
import uuid
import time

# ENHANCED: Import semantic chunks service instead of legacy retrieval QA service
from app.services.semantic_chunks_service import SemanticChunksService
from app.services.supabase_client import SupabaseService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger("bpt-qa-routes")

router = APIRouter(prefix="/qa", tags=["Q&A"])

# ENHANCED: Use semantic chunks service
semantic_service: Optional[SemanticChunksService] = None
supabase_service: Optional[SupabaseService] = None
embedding_service: Optional[EmbeddingService] = None

def init_qa_routes(semantic_svc: SemanticChunksService, supabase_svc: SupabaseService):
    """Initialize the routes with enhanced service dependencies"""
    global semantic_service, supabase_service, embedding_service
    semantic_service = semantic_svc
    supabase_service = supabase_svc
    embedding_service = EmbeddingService()  # Initialize embedding service

def is_analytical_question(question: str) -> bool:
    """
    Detect questions requiring comprehensive analysis or enumeration.
    Domain-agnostic patterns for analytical questions.
    """
    analytical_patterns = [
        r'\bhow many\b', r'\blist\b', r'\ball\b', r'\bevery\b',
        r'\bcount\b', r'\benumerate\b', r'\bwhat.*mentioned\b',
        r'\bwhat.*said about\b', r'\bwhat.*discussed\b',
        r'\bwhat.*talked about\b', r'\bwhat.*covered\b',
        r'\btell me about\b', r'\bexplain.*about\b',
        r'\bdetails about\b', r'\binformation about\b'
    ]
    return any(re.search(pattern, question.lower()) for pattern in analytical_patterns)

def extract_entities_summary(search_results: List[Dict]) -> Dict[str, List[str]]:
    """
    Extract and categorize entities from search results.
    Domain-agnostic entity extraction.
    """
    entities_by_type = {}
    
    for result in search_results:
        entities = result.get('entities', [])
        if isinstance(entities, list):
            for entity in entities:
                if isinstance(entity, dict):
                    entity_type = entity.get('type', 'MISC')
                    entity_text = entity.get('text', '')
                    
                    if entity_type not in entities_by_type:
                        entities_by_type[entity_type] = set()
                    
                    if entity_text:
                        entities_by_type[entity_type].add(entity_text)
    
    # Convert sets to lists for JSON serialization
    return {k: list(v) for k, v in entities_by_type.items()}

@router.post("")
async def answer_question(request: Request):
    """
    Answer a question based on the content of transcripts using enhanced RAG system
    """
    if not semantic_service:
        raise HTTPException(status_code=500, detail="Enhanced QA service not initialized")
        
    try:
        data = await request.json()
        question = data.get("question")
        transcript_id = data.get("transcript_id")  # Optional
        session_id = data.get("session_id")  # Optional for chat context
        
        # If session_id is provided but transcript_id is not, use session_id as transcript_id
        if not transcript_id and session_id:
            transcript_id = session_id
        
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
        
        # ENHANCED: Use semantic chunks service for question answering
        response = await enhanced_answer_question(question, transcript_id)
        
        if not response["success"]:
            raise HTTPException(status_code=500, detail=response.get("error", "Failed to generate answer"))
            
        return response
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error in enhanced answer_question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def enhanced_answer_question(question: str, transcript_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Enhanced question answering using semantic chunks and vector search with comprehensive responses
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing enhanced question: '{question}' for transcript: {transcript_id or 'all'}")
        
        # Step 1: Generate query embedding
        query_embedding = await embedding_service.get_embeddings([question])
        if not query_embedding:
            return {
                "success": False,
                "error": "Failed to generate query embedding",
                "confidence": 0.0
            }
        
        # Step 2: Enhanced search - retrieve MORE chunks for comprehensive analysis
        is_analytical = is_analytical_question(question)
        match_count = 25 if is_analytical else 20  # INCREASED from 15/10
        
        search_results = await semantic_service.search_semantic_chunks(
            query_embedding[0],
            transcript_id=transcript_id,
            match_count=match_count
        )
        
        # FALLBACK: If vector search returns no results, try text-based search
        if not search_results:
            logger.warning(f"Vector search returned no results, falling back to text search for: {question}")
            
            # Simple text-based search as fallback
            try:
                if not supabase_service:
                    return {
                        "success": False,
                        "error": "Database service not available for fallback search",
                        "confidence": 0.0
                    }
                
                # Search for chunks containing keywords from the question
                question_keywords = [kw.strip() for kw in question.lower().split() if len(kw.strip()) > 2]
                
                if question_keywords:
                    # Use Supabase's safe parameter binding instead of string concatenation
                    query_builder = supabase_service.client.table("semantic_chunks").select("*")
                    
                    if transcript_id:
                        # Filter by transcript first
                        query_builder = query_builder.eq("transcript_id", transcript_id)
                    
                    # Use the first significant keyword for primary search
                    # Supabase client doesn't support complex OR conditions easily,
                    # so we use the most significant keyword for better results
                    primary_keyword = question_keywords[0]
                    query_builder = query_builder.ilike("text", f"%{primary_keyword}%")
                    
                    text_search_result = query_builder.limit(10).execute()
                    
                    if text_search_result.data:
                        # Convert to expected format
                        search_results = []
                        for chunk in text_search_result.data:
                            search_results.append({
                                'id': chunk.get('id'),
                                'transcript_id': chunk.get('transcript_id'),
                                'text': chunk.get('text', ''),
                                'similarity': 0.7,  # Assign moderate similarity for text matches
                                'entities': chunk.get('entities', [])
                            })
                        
                        logger.info(f"Text search fallback found {len(search_results)} chunks")
                    
            except Exception as e:
                logger.error(f"Text search fallback failed: {e}")
        
        if not search_results:
            return {
                "success": True,
                "answer": "I don't have enough information to answer this question based on the available transcripts.",
                "confidence": 0.0,
                "sources": [],
                "processing_time": time.time() - start_time,
                "metadata": {
                    "retrieval_method": "enhanced_semantic",
                    "chunks_retrieved": 0,
                    "analytical_question": is_analytical
                }
            }
        
        # Step 3: Enhanced context building with MORE comprehensive detail
        context_parts = []
        sources = []
        
        # Sort by similarity to prioritize most relevant content
        search_results.sort(key=lambda x: x.get('similarity', 0.0), reverse=True)
        
        for i, result in enumerate(search_results, 1):
            text = result.get('text', '')
            similarity = result.get('similarity', 0.0)
            
            # Include more chunks with lower similarity threshold for comprehensive coverage
            if similarity >= 0.65:  # LOWERED from default to include more content
                # Enhanced context with similarity scores for better LLM understanding
                context_parts.append(f"[Source {i} - Relevance: {similarity:.3f}] {text}")
                
                sources.append({
                    'chunk_id': result.get('id', ''),
                    'transcript_id': result.get('transcript_id', transcript_id or ''),
                    'similarity': similarity,
                    'text_preview': text[:200] + '...' if len(text) > 200 else text,
                    'entities': result.get('entities', [])[:5]  # Top 5 entities
                })
        
        # Ensure we have substantial context - if not enough high-similarity chunks, include more
        if len(context_parts) < 8:  # Ensure minimum comprehensive context
            for i, result in enumerate(search_results, len(context_parts) + 1):
                if len(context_parts) >= 12:  # Cap at reasonable limit
                    break
                    
                text = result.get('text', '')
                similarity = result.get('similarity', 0.0)
                
                # Include additional chunks with lower threshold
                if similarity >= 0.55 and result not in [s for s in sources]:
                    context_parts.append(f"[Source {i} - Relevance: {similarity:.3f}] {text}")
                    sources.append({
                        'chunk_id': result.get('id', ''),
                        'transcript_id': result.get('transcript_id', transcript_id or ''),
                        'similarity': similarity,
                        'text_preview': text[:200] + '...' if len(text) > 200 else text,
                        'entities': result.get('entities', [])[:5]
                    })
        
        context = "\n\n".join(context_parts)
        
        # Step 4: Enhanced LLM response generation
        answer = await generate_enhanced_llm_response(question, context, is_analytical, search_results)
        
        # Step 5: Calculate confidence based on search quality
        avg_similarity = sum(r.get('similarity', 0) for r in search_results) / len(search_results)
        confidence = min(avg_similarity * 1.2, 1.0)  # Boost confidence slightly, cap at 1.0
        
        end_time = time.time()
        
        return {
            "success": True,
            "answer": answer,
            "confidence": round(confidence, 2),
            "sources": sources,
            "processing_time": round(end_time - start_time, 2),
            "metadata": {
                "retrieval_method": "enhanced_semantic",
                "chunks_retrieved": len(search_results),
                "avg_similarity": round(avg_similarity, 3),
                "transcript_id": transcript_id,
                "analytical_question": is_analytical,
                "enhancement_level": "comprehensive"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced_answer_question: {e}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "confidence": 0.0,
            "processing_time": time.time() - start_time
        }

async def generate_enhanced_llm_response(question: str, context: str, is_analytical: bool, search_results: List[Dict]) -> str:
    """
    Generate comprehensive LLM response with enhanced prompting for detailed analysis
    """
    try:
        import openai
        import os
        
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Enhanced system prompt for comprehensive responses
        if is_analytical:
            # Extract structured information for analytical questions
            entities_summary = extract_entities_summary(search_results)
            
            system_prompt = """You are a comprehensive analyst that provides detailed, thorough responses based on transcript discussions.

INSTRUCTIONS FOR ANALYTICAL QUESTIONS:
1. Provide complete, detailed analysis covering ALL relevant points from the context
2. Structure responses with clear flow and comprehensive coverage
3. Include specific details, numbers, and nuanced perspectives mentioned
4. For counting/enumeration questions, be thorough and systematic
5. Explain the reasoning and context behind statements
6. Cover both immediate observations and broader implications
7. Maintain accuracy while being thorough and informative
8. Use natural, flowing language that connects related concepts
9. When listing items, be comprehensive and include all mentioned elements

Be comprehensive and detailed while staying grounded in the provided context. Aim for 150-200 words for thorough coverage."""
            
            # Enhanced context with structured data
            structured_info = ""
            if entities_summary:
                structured_info = f"\n\nStructured Analysis - Key Topics/Entities Mentioned:\n"
                for entity_type, entities in entities_summary.items():
                    if entities:
                        structured_info += f"- {entity_type}: {', '.join(entities[:10])}\n"  # Limit to avoid overfitting
            
            user_prompt = f"""Context from transcript discussions:
{context}

Question: {question}

Please provide a comprehensive, detailed response covering ALL relevant information from the context. Include specific details, numbers, and nuanced perspectives. Be thorough and systematic in your analysis.

IMPORTANT: The context contains multiple sources with relevance scores. Use ALL relevant sources to provide a complete picture. Don't limit yourself to only the highest-scoring sources - synthesize information from multiple sources to give a comprehensive answer."""
            
        else:
            # Standard comprehensive prompt for non-analytical questions
            system_prompt = """You are a knowledgeable assistant that provides detailed, informative responses based on transcript discussions.

INSTRUCTIONS:
1. Provide comprehensive answers based on the provided context
2. Include specific details, numbers, and perspectives mentioned
3. Explain the reasoning and context behind statements
4. Cover related points and implications when relevant
5. Maintain accuracy while being thorough and informative
6. Use natural, flowing language that connects concepts
7. If the context doesn't contain enough information, state this clearly

Be detailed and informative while staying grounded in the provided context. Aim for 120-180 words for good coverage."""
            
            user_prompt = f"""Context from transcript discussions:
{context}

Question: {question}

Please provide a detailed, comprehensive answer based on the context above. Include specific information and explain the broader context when relevant.

IMPORTANT: The context contains multiple sources with relevance scores. Use ALL relevant sources to provide a complete picture and synthesize information from multiple sources for a thorough response."""
        
        # Enhanced generation parameters
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use efficient model for Q&A
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,  # Increased from 500 for comprehensive responses
            temperature=0.3   # Increased from 0.1 for better elaboration while maintaining accuracy
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Error generating enhanced LLM response: {e}")
        return "I encountered an error while generating the response. Please try again."

@router.post("/feedback")
async def submit_feedback(request: Request):
    """Submit feedback on a Q&A response"""
    if not supabase_service:
        raise HTTPException(status_code=500, detail="Database service not initialized")
        
    try:
        data = await request.json()
        question_id = data.get("question_id") or str(uuid.uuid4())
        question = data.get("question")
        answer = data.get("answer")
        rating = data.get("rating")
        feedback = data.get("feedback")
        transcript_id = data.get("transcript_id")
        
        if not question or not answer:
            raise HTTPException(status_code=400, detail="Question and answer are required")
            
        if not supabase_service.is_connected():
            raise HTTPException(status_code=500, detail="Database not connected")
            
        # Store feedback in database
        result = supabase_service.client.table("user_feedback").insert({
            "question_id": question_id,
            "question": question,
            "answer": answer,
            "rating": rating,
            "feedback": feedback,
            "transcript_id": transcript_id
        }).execute()
        
        return {"success": True, "message": "Feedback submitted successfully"}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_available_sessions(limit: int = 100):
    """
    Get available transcript sessions for the frontend selector.
    This is a public endpoint for the transcript selector functionality.
    """
    try:
        if not supabase_service:
            raise HTTPException(status_code=500, detail="Supabase service not initialized")
        
        # Get transcripts from Supabase
        result = await supabase_service.get_transcripts()
        
        if not result.get("success"):
            logger.error(f"Error retrieving transcripts: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error", "Failed to retrieve transcripts"),
                "sessions": [],
                "total": 0
            }
        
        # Extract and format transcripts as sessions
        transcripts = result.get("data", [])
        
        # Format transcripts to match expected session format
        sessions = []
        for transcript in transcripts[:limit]:
            # Map database fields to expected frontend format
            session = {
                "id": transcript.get("transcript_id"),  # Use transcript_id as id
                "session_id": transcript.get("transcript_id"),  # Also provide session_id for compatibility
                "name": transcript.get("title", f"Transcript {transcript.get('transcript_id', 'unknown')}"),
                "title": transcript.get("title", f"Transcript {transcript.get('transcript_id', 'unknown')}"),
                "created_at": transcript.get("created_at"),
                "last_modified": transcript.get("created_at"),  # Use created_at as last_modified since no updated_at
                "metadata": {
                    "word_count": transcript.get("word_count", 0),
                    "duration_seconds": transcript.get("duration_seconds", 0),
                    "source": transcript.get("source", "unknown"),
                    "status": "active"
                }
            }
            sessions.append(session)
        
        return {
            "success": True,
            "sessions": sessions,
            "total": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Error in get_available_sessions: {str(e)}")
        return {
            "success": False,
            "error": f"Error retrieving sessions: {str(e)}",
            "sessions": [],
            "total": 0
        }

@router.post("/process-transcript")
async def process_transcript(request: Request):
    """
    Process an uploaded transcript file and store it in the system using proper semantic chunking.
    This endpoint handles transcript upload and processing for the frontend.
    """
    try:
        if not supabase_service:
            raise HTTPException(status_code=500, detail="Supabase service not initialized")
        
        if not semantic_service:
            raise HTTPException(status_code=500, detail="Semantic service not initialized")
            
        if not embedding_service:
            raise HTTPException(status_code=500, detail="Embedding service not initialized")
        
        data = await request.json()
        content = data.get("content")
        filename = data.get("filename", "uploaded_transcript.txt")
        
        if not content:
            raise HTTPException(status_code=400, detail="Transcript content is required")
        
        # Generate a unique transcript ID
        transcript_id = f"transcript_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # Create metadata for transcript
        metadata = {
            "title": filename.replace('.txt', '').replace('.md', ''),
            "source": "streamlit_upload",
            "filename": filename,
            "word_count": len(content.split()),
            "upload_timestamp": time.time()
        }
        
        logger.info(f"Processing transcript {transcript_id} with {metadata['word_count']} words")
        
        # Step 1: Use proper semantic chunking
        from services.semantic_chunker import SemanticChunker
        
        chunker = SemanticChunker(domain_type="financial")
        semantic_chunks = chunker.chunk_text(content, source_id=transcript_id)
        
        if not semantic_chunks:
            raise HTTPException(status_code=500, detail="Failed to create semantic chunks")
            
        logger.info(f"Created {len(semantic_chunks)} semantic chunks")
        
        # Step 2: Generate embeddings for chunks
        chunk_texts = [chunk.text for chunk in semantic_chunks]
        embeddings = await embedding_service.get_embeddings(chunk_texts)
        
        if not embeddings or len(embeddings) != len(semantic_chunks):
            raise HTTPException(status_code=500, detail="Failed to generate embeddings for chunks")
            
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Step 3: Store transcript metadata in transcripts table
        transcript_data = {
            "transcript_id": transcript_id,
            "title": metadata["title"],
            "word_count": metadata["word_count"],
            "source": metadata["source"]
        }
        
        transcript_result = supabase_service.client.table("transcripts").insert(transcript_data).execute()
        
        if hasattr(transcript_result, 'error') and transcript_result.error is not None:
            logger.error(f"Error storing transcript: {transcript_result.error}")
            raise HTTPException(status_code=500, detail=f"Failed to store transcript: {transcript_result.error}")
        
        # Step 4: Store semantic chunks with embeddings
        store_result = await semantic_service.store_semantic_chunks(
            chunks=semantic_chunks,
            embeddings=embeddings,
            transcript_id=transcript_id
        )
        
        if not store_result.get("success"):
            logger.error(f"Error storing semantic chunks: {store_result.get('error')}")
            raise HTTPException(status_code=500, detail=f"Failed to store semantic chunks: {store_result.get('error')}")
        
        chunks_stored = store_result.get("chunks_stored", 0)
        processing_time = store_result.get("processing_time", 0)
        
        logger.info(f"Successfully stored transcript {transcript_id} with {chunks_stored} semantic chunks")
        
        return {
            "success": True,
            "session_id": transcript_id,
            "stats": {
                "chunks_created": chunks_stored,
                "word_count": metadata["word_count"],
                "semantic_chunks": len(semantic_chunks),
                "embeddings_generated": len(embeddings)
            },
            "processing_time": processing_time
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error in process_transcript: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) 