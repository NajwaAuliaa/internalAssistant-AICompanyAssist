from depedencies import *
# Language detection removed - not needed for core functionality
from internal_assistant_core import llm, retriever, vectorstore, blob_container, doc_client, settings
import base64
import re
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import Dict, List, Any, Optional
import hashlib
import time
import sys
from io import BytesIO
import contextlib

tokenizer = tiktoken.get_encoding("cl100k_base")
def tiktoken_len(text):
    return len(tokenizer.encode(text))

def _make_safe_doc_id(blob_name: str) -> str:
    return base64.urlsafe_b64encode(blob_name.encode()).decode()

# === Advanced text cleaning dengan preserve struktur ===
def _clean_text(text: str) -> str:
    if not text:
        return ""
    
    # Preserve struktur dokumen yang penting
    txt = text.replace("\u00a0", " ")            # Non-breaking space
    txt = re.sub(r"[•●▪∙◦]", "- ", txt)          # Bullet points dengan spasi
    txt = re.sub(r'[ \t]+', ' ', txt)            # Multiple spaces jadi single space
    txt = re.sub(r'\n{4,}', '\n\n\n', txt)       # Max 3 newlines berturut-turut
    
    # Preserve numbering dan struktur hierarki
    txt = re.sub(r'(\d+)\.(\s*)', r'\1. ', txt)  # Normalize numbering
    txt = re.sub(r'(\d+\.\d+)\.(\s*)', r'\1. ', txt)  # Sub-numbering
    
    return txt.strip()

# === Ekstraksi teks yang comprehensive dan general ===

def _extract_text_with_docint(binary: bytes) -> Dict[str, List[Dict[str, Any]]]:
    """Extract structured text dengan metadata posisi dan context - GENERAL untuk semua dokumen."""
    try:
        # ✅ Force baca semua halaman
        poller = doc_client.begin_analyze_document(
            "prebuilt-layout",
            document=BytesIO(binary),   # lebih aman untuk file besar
            pages="1-15"               # ambil semua halaman
        )
        res = poller.result()
    except Exception as e:
        print(f"Error analyzing document: {e}")
        return {"sections": [], "raw_tables": [], "document_structure": []}

    # ✅ Debug jumlah halaman yang berhasil dibaca
    if hasattr(res, "pages"):
        print(f"✅ Document Intelligence extracted {len(res.pages)} pages")

    processed = {
        "sections": [],  # Semua bagian dengan metadata
        "raw_tables": [],
        "document_structure": []  # Struktur hierarki dokumen
    }

    current_section = None
    section_counter = 0

    # Process paragraphs dengan context dan posisi - GENERAL approach
    if hasattr(res, "paragraphs"):
        for idx, para in enumerate(res.paragraphs):
            role = getattr(para, "role", None)
            text = _clean_text(para.content)
            if not text or len(text) < 10:  # Skip very short content
                continue

            content_type = _classify_content_type(text, role)
            
            section_data = {
                "content": text,
                "type": content_type,
                "role": role,
                "position": idx,
                "tokens": tiktoken_len(text)
            }

            # Jika heading, mulai section baru
            if content_type in ["title", "heading", "section_header", "chapter", "subsection"]:
                if current_section:
                    processed["sections"].append(current_section)
                
                current_section = {
                    "header": text,
                    "type": content_type,
                    "content_parts": [section_data],
                    "section_id": section_counter,
                    "total_tokens": tiktoken_len(text)
                }
                section_counter += 1
            else:
                if current_section:
                    current_section["content_parts"].append(section_data)
                    current_section["total_tokens"] += tiktoken_len(text)
                else:
                    current_section = {
                        "header": "Document Content",
                        "type": "content",
                        "content_parts": [section_data],
                        "section_id": section_counter,
                        "total_tokens": tiktoken_len(text)
                    }
                    section_counter += 1

            processed["document_structure"].append(section_data)

        if current_section:
            processed["sections"].append(current_section)

    # Process tables dengan context yang lebih baik
    if hasattr(res, "tables"):
        for table_idx, table in enumerate(res.tables):
            rows = {}
            headers = []
            
            for cell in table.cells:
                content = _clean_text(cell.content)
                if cell.row_index not in rows:
                    rows[cell.row_index] = {}
                rows[cell.row_index][cell.column_index] = content
                
                if cell.row_index == 0:
                    headers.append(content)

            table_rows = []
            for r in sorted(rows.keys()):
                row_data = [rows[r].get(c, "") for c in sorted(rows[r].keys())]
                table_rows.append(" | ".join(row_data))
            
            table_text = "\n".join(table_rows)
            
            processed["raw_tables"].append({
                "content": table_text,
                "headers": headers,
                "table_id": table_idx,
                "tokens": tiktoken_len(table_text)
            })

    return processed


def _classify_content_type(text: str, role: Optional[str] = None) -> str:
    """Klasifikasi jenis konten GENERAL untuk semua jenis dokumen."""
    text_upper = text.upper()
    text_lower = text.lower()
    
    # Deteksi berdasarkan role
    if role and "title" in role.lower():
        return "title"
    if role and "heading" in role.lower():
        return "heading"
    
    # Pattern umum untuk berbagai bahasa dan jenis dokumen
    # Table of Contents patterns
    if any(keyword in text_upper for keyword in 
           ["DAFTAR ISI", "TABLE OF CONTENTS", "CONTENTS", "INDEX", "INDEKS"]):
        return "table_of_contents"
    
    # Chapter/Section patterns
    if re.match(r'^(BAB|CHAPTER|SECTION|BAGIAN)\s*\d+', text_upper):
        return "chapter"
    
    if re.match(r'^\d+\.', text.strip()):  # Dimulai dengan nomor
        return "section_header"
    
    if re.match(r'^\d+\.\d+', text.strip()):  # Sub section
        return "subsection_header"
    
    # Appendix patterns
    if any(keyword in text_upper for keyword in 
           ["APPENDIX", "LAMPIRAN", "ANNEX", "ATTACHMENT"]):
        return "appendix"
    
    # General important sections
    if any(keyword in text_upper for keyword in 
           ["PURPOSE", "TUJUAN", "VISION", "VISI", "MISSION", "MISI", 
            "OBJECTIVE", "SASARAN", "GOAL", "TARGET", "INTRODUCTION", 
            "PENDAHULUAN", "OVERVIEW", "RINGKASAN", "SUMMARY",
            "CONCLUSION", "KESIMPULAN", "RECOMMENDATION", "REKOMENDASI"]):
        return "purpose_statement"
    
    # Procedure/Process patterns
    if any(keyword in text_upper for keyword in 
           ["PROCEDURE", "PROSEDUR", "PROCESS", "PROSES", "WORKFLOW",
            "LANGKAH", "TAHAP", "STEPS", "CARA"]):
        return "detailed_content"
    
    # Policy/Rule patterns
    if any(keyword in text_upper for keyword in 
           ["POLICY", "KEBIJAKAN", "RULE", "ATURAN", "REGULATION",
            "REGULASI", "GUIDELINE", "PANDUAN"]):
        return "detailed_content"
    
    # Long detailed content
    if len(text.split()) > 100:
        return "detailed_content"
    
    # Table content detection
    if any(char in text for char in ["|", ":", "─", "┌", "└"]) or \
       (text.count("|") > 2 and "\n" in text):
        return "table_content"
    
    # List content
    if text.count("- ") > 2 or text.count("• ") > 2:
        return "content"
    
    return "content"

# === Cost-optimized intelligent chunking strategy ===
def _create_intelligent_chunks(doc_data: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
    """Create chunks yang cost-efficient untuk Azure AI Search."""
    chunks = []
    
    # Process sections dengan cost optimization
    for section in doc_data.get("sections", []):
        section_chunks = _process_section_intelligently(section)
        chunks.extend(section_chunks)
    
    # Process tables sebagai chunks terpisah dengan optimization
    for table in doc_data.get("raw_tables", []):
        if table["tokens"] > 3500:  # Table besar dipecah dengan target yang lebih besar
            table_chunks = _split_large_table(table)
            chunks.extend(table_chunks)
        else:
            chunks.append({
                "content": f"=== TABLE ===\n{table['content']}",
                "type": "table",
                "metadata": {"table_id": table["table_id"], "headers": table["headers"]},
                "tokens": table["tokens"]
            })
    
    # Deduplicate untuk avoid redundant storage
    chunks = _deduplicate_chunks(chunks)
    
    return chunks

def _process_section_intelligently(section: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process section dengan cost optimization - larger chunks untuk reduce storage cost."""
    chunks = []
    section_header = section["header"]
    content_parts = section["content_parts"]
    
    # Target chunk size yang lebih besar untuk cost efficiency (3000-4000 tokens)
    target_chunk_size = 3500
    
    # Jika section kecil atau medium, jadikan satu chunk
    if section["total_tokens"] <= target_chunk_size:
        full_content = f"=== {section_header} ===\n"
        full_content += "\n\n".join([part["content"] for part in content_parts])
        
        chunks.append({
            "content": full_content,
            "type": section["type"],
            "metadata": {
                "section_header": section_header,
                "section_id": section["section_id"],
                "is_complete_section": True
            },
            "tokens": section["total_tokens"]
        })
    else:
        # Section besar, bagi dengan larger chunks untuk cost efficiency
        current_chunk_parts = []
        current_tokens = tiktoken_len(f"=== {section_header} ===\n")
        
        for part in content_parts:
            # Target yang lebih besar untuk reduce number of chunks
            if current_tokens + part["tokens"] > target_chunk_size:
                if current_chunk_parts:
                    # Create chunk
                    chunk_content = f"=== {section_header} ===\n"
                    chunk_content += "\n\n".join([p["content"] for p in current_chunk_parts])
                    
                    chunks.append({
                        "content": chunk_content,
                        "type": section["type"],
                        "metadata": {
                            "section_header": section_header,
                            "section_id": section["section_id"],
                            "is_partial_section": True,
                            "chunk_part": len(chunks) + 1
                        },
                        "tokens": current_tokens
                    })
                
                # Start new chunk
                current_chunk_parts = [part]
                current_tokens = tiktoken_len(f"=== {section_header} ===\n") + part["tokens"]
            else:
                current_chunk_parts.append(part)
                current_tokens += part["tokens"]
        
        # Add final chunk if exists
        if current_chunk_parts:
            chunk_content = f"=== {section_header} ===\n"
            chunk_content += "\n\n".join([p["content"] for p in current_chunk_parts])
            
            chunks.append({
                "content": chunk_content,
                "type": section["type"],
                "metadata": {
                    "section_header": section_header,
                    "section_id": section["section_id"],
                    "is_partial_section": True,
                    "chunk_part": len(chunks) + 1
                },
                "tokens": current_tokens
            })
    
    return chunks

def _split_large_table(table: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Split table besar dengan preserve headers dan target size yang lebih besar."""
    chunks = []
    lines = table["content"].split("\n")
    headers = lines[0] if lines else ""
    
    current_chunk_lines = [headers]  # Always include headers
    current_tokens = tiktoken_len(headers)
    
    # Target size yang lebih besar untuk tables
    target_size = 3000
    
    for line in lines[1:]:  # Skip header line
        line_tokens = tiktoken_len(line)
        if current_tokens + line_tokens > target_size:
            # Create chunk
            chunk_content = f"=== TABLE (Part {len(chunks) + 1}) ===\n"
            chunk_content += "\n".join(current_chunk_lines)
            
            chunks.append({
                "content": chunk_content,
                "type": "table",
                "metadata": {
                    "table_id": table["table_id"],
                    "headers": table["headers"],
                    "is_partial_table": True,
                    "part": len(chunks) + 1
                },
                "tokens": current_tokens
            })
            
            # Start new chunk with headers
            current_chunk_lines = [headers, line]
            current_tokens = tiktoken_len(headers) + line_tokens
        else:
            current_chunk_lines.append(line)
            current_tokens += line_tokens
    
    # Add final chunk
    if len(current_chunk_lines) > 1:  # More than just headers
        chunk_content = f"=== TABLE (Part {len(chunks) + 1}) ===\n"
        chunk_content += "\n".join(current_chunk_lines)
        
        chunks.append({
            "content": chunk_content,
            "type": "table",
            "metadata": {
                "table_id": table["table_id"],
                "headers": table["headers"],
                "is_partial_table": True,
                "part": len(chunks) + 1
            },
            "tokens": current_tokens
        })
    
    return chunks

def _deduplicate_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate chunks untuk cost optimization."""
    unique_chunks = []
    seen_hashes = set()
    
    for chunk in chunks:
        # Create content hash untuk deduplication
        content_hash = hashlib.md5(chunk["content"].encode()).hexdigest()
        
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique_chunks.append(chunk)
    
    return unique_chunks

# === Enhanced indexing pipeline - tetap nama function yang sama ===
def process_and_index_docs(prefix: str = "") -> Dict[str, Any]:
    """Process dan index dokumen dengan cost optimization - support semua prefix termasuk kosong."""
    indexed, skipped, errors = 0, 0, []
    total_chunks = 0
    
    # Jika prefix kosong, process semua blobs
    if prefix:
        blob_list = blob_container.list_blobs(name_starts_with=prefix)
    else:
        blob_list = blob_container.list_blobs()

    print(f"Starting to process documents with prefix: '{prefix}'")
    
    for b in blob_list:
        try:
            print(f"Processing: {b.name}")
            blob_client = blob_container.get_blob_client(b.name)
            content_bytes = blob_client.download_blob().readall()

            # Extract dengan struktur yang comprehensive dan general
            doc_data = _extract_text_with_docint(content_bytes)
            
            if not doc_data.get("sections") and not doc_data.get("raw_tables"):
                skipped += 1
                print(f"Skipped {b.name}: No content extracted")
                continue

            # Create cost-optimized chunks
            chunks = _create_intelligent_chunks(doc_data)
            
            if not chunks:
                skipped += 1
                print(f"Skipped {b.name}: No chunks created")
                continue

            # Index each chunk dengan cost-efficient metadata
            for i, chunk_data in enumerate(chunks):
                chunk_id = f"{_make_safe_doc_id(b.name)}_{i}"
                
                # Optimized metadata - only essential fields
                base_metadata = {
                    "source": b.name,
                    "chunk_index": i,
                    "content_type": chunk_data["type"],
                    "token_count": chunk_data["tokens"],
                    "total_chunks": len(chunks)
                }
                
                # Add specific metadata dari chunk
                base_metadata.update(chunk_data.get("metadata", {}))
                
                try:
                    vectorstore.add_texts(
                        [chunk_data["content"]], 
                        metadatas=[base_metadata], 
                        ids=[chunk_id]
                    )
                except Exception as e:
                    print(f"Error indexing chunk {chunk_id}: {e}")
                    continue
            
            total_chunks += len(chunks)
            print(f"Indexed {b.name}: {len(chunks)} chunks")
            indexed += 1
            
            # Add small delay untuk avoid rate limiting
            time.sleep(0.1)

        except Exception as e:
            error_msg = f"{b.name}: {str(e)}"
            errors.append(error_msg)
            print(f"Error processing {b.name}: {e}")

    return {
        "indexed": indexed, 
        "skipped": skipped, 
        "errors": errors,
        "total_chunks": total_chunks,
        "avg_chunks_per_doc": total_chunks / max(indexed, 1)
    }

# === Cost-optimized RAG answering dengan nama function yang sama ===
def rag_answer(query: str, max_docs: int = 10) -> str:
    """Cost-optimized RAG dengan smart retrieval untuk minimize Azure AI Search costs."""
    
    # Single-stage optimized retrieval
    retrieved_docs = _multi_stage_retrieval(query, max_docs)
    
    if not retrieved_docs:
        return "Maaf, tidak ada informasi yang relevan di basis dokumen internal."

    # Build context efficiently
    context = _build_comprehensive_context(retrieved_docs, query)
    
    # Default to Indonesian language
    lang = "id"

    # Build system prompt
    sys_prompt = _build_advanced_system_prompt(lang, query, retrieved_docs)
    
    sys = SystemMessage(content=sys_prompt)
    prompt = ChatPromptTemplate.from_messages([
        sys,
        ("human", "Question: {q}\n\nContext:\n{ctx}")
    ])

    chain = prompt | llm
    resp = chain.invoke({"q": query, "ctx": context})
    return resp.content

def _multi_stage_retrieval(query: str, max_docs: int) -> List[Any]:
    """Cost-optimized single retrieval call untuk minimize costs."""
    try:
        # Single retrieval call dengan slightly higher k untuk better coverage
        docs = retriever.get_relevant_documents(
            query, 
            search_kwargs={"k": min(max_docs + 2, 15)}  # Slight buffer, but capped
        )
        
        # Simple reranking without additional calls
        return _rerank_documents(docs, query, max_docs)
        
    except Exception as e:
        print(f"Error in retrieval: {e}")
        return []

def _rerank_documents(docs: List[Any], query: str, max_docs: int) -> List[Any]:
    """Simple reranking tanpa additional API calls."""
    scored_docs = []
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    for doc in docs:
        score = 0
        content = doc.page_content.lower()
        metadata = doc.metadata
        
        # Simple relevance scoring
        for word in query_words:
            if word in content:
                score += content.count(word) * 10
        
        # Boost for complete sections
        if metadata.get("is_complete_section", False):
            score += 50
        
        # Content type bonuses
        content_type = metadata.get("content_type", "")
        if "table_of_contents" in content_type and any(toc_word in query_lower for toc_word in ["daftar", "isi", "contents"]):
            score += 100
        
        if "table" in content_type and any(table_word in query_lower for table_word in ["tabel", "table", "data"]):
            score += 30
        
        # Length bonus untuk comprehensive content
        if len(doc.page_content) > 500:
            score += 20
        
        scored_docs.append((doc, score))
    
    # Sort and return top docs
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, score in scored_docs[:max_docs]]

def _build_comprehensive_context(docs: List[Any], query: str) -> str:
    """Build context yang efficient untuk reduce token usage."""
    context_parts = []
    
    # Simple context building
    for i, doc in enumerate(docs):
        metadata = doc.metadata
        source = metadata.get('source', 'unknown')
        content_type = metadata.get('content_type', 'content')
        section_header = metadata.get('section_header', '')
        
        # Add metadata info untuk context
        meta_info = f"[SOURCE: {source} | TYPE: {content_type}"
        if section_header:
            meta_info += f" | SECTION: {section_header}"
        meta_info += "]"
        
        context_parts.append(f"{meta_info}\n{doc.page_content}")
    
    return "\n\n".join(context_parts)

def _build_advanced_system_prompt(lang: str, query: str, docs: List[Any]) -> str:
    """Build efficient system prompt."""
    
    # Analyze available content types
    content_types = set()
    has_complete_sections = False
    has_tables = False
    
    for doc in docs:
        content_types.add(doc.metadata.get('content_type', 'content'))
        if doc.metadata.get('is_complete_section'):
            has_complete_sections = True
        if 'table' in doc.metadata.get('content_type', ''):
            has_tables = True
    
    if lang == "id":
        base_prompt = (
            "Anda adalah asisten ahli dokumen internal yang memberikan jawaban LENGKAP dan AKURAT. "
            "Tugas Anda adalah menjawab pertanyaan berdasarkan konteks yang diberikan dengan detail maksimal. "
        )
        
        instructions = [
            "1. Berikan jawaban yang KOMPREHENSIF berdasarkan SEMUA informasi relevan dalam konteks",
            "2. Jika ada struktur hierarki (daftar, bab, sub-bab), tampilkan dengan format yang jelas",
            "3. Gunakan SEMUA detail yang tersedia - jangan ringkas atau potong informasi",
            "4. Jika ada tabel, tampilkan dengan format yang mudah dibaca",
            "5. JANGAN PERNAH menyuruh user membaca dokumen asli atau mereferensikan ke sumber lain",
            "6. Jika informasi tersebar di beberapa bagian, gabungkan menjadi jawaban yang koheren",
            "7. Berikan jawaban dalam bahasa Indonesia yang natural dan profesional"
        ]
        
        if "daftar isi" in query.lower() or "contents" in query.lower():
            instructions.append("8. Untuk daftar isi: tampilkan SEMUA item dengan hierarki yang lengkap dan jelas")
        
        if has_tables:
            instructions.append("8. Format tabel dengan rapi menggunakan struktur yang mudah dibaca")
        
        full_prompt = base_prompt + "\n\nINSTRUKSI:\n" + "\n".join(instructions)
        
    else:
        base_prompt = (
            "You are an expert internal document assistant that provides COMPLETE and ACCURATE answers. "
            "Your task is to answer questions based on the given context with maximum detail. "
        )
        
        instructions = [
            "1. Provide COMPREHENSIVE answers based on ALL relevant information in the context",
            "2. If there are hierarchical structures (lists, chapters, sub-chapters), display them clearly",
            "3. Use ALL available details - don't summarize or cut information",
            "4. If there are tables, display them in readable format",
            "5. NEVER direct users to read original documents or reference other sources",
            "6. If information is spread across sections, combine into coherent answer",
            "7. Provide answers in natural and professional language"
        ]
        
        if "table of contents" in query.lower() or "contents" in query.lower():
            instructions.append("8. For table of contents: display ALL items with complete and clear hierarchy")
        
        if has_tables:
            instructions.append("8. Format tables neatly using readable structure")
        
        full_prompt = base_prompt + "\n\nINSTRUCTIONS:\n" + "\n".join(instructions)
    
    return full_prompt

# Enhanced tool definition - tetap nama yang sama
rag_tool = StructuredTool.from_function(
    name="qna_internal",
    description=(
        "Cost-optimized comprehensive Q&A system for ALL internal documents "
        "via Azure AI Search. Handles any document type (SOPs, procedures, policies, "
        "handbooks, reports, etc.) with efficient retrieval to minimize Azure costs "
        "while maintaining high accuracy and completeness."
    ),
    func=rag_answer,
)

# #================= DEBUG =================
# def debug_process_docs(prefix: str = "sop/"):
#     """Debug pipeline end-to-end tanpa indexing ke Azure AI Search.
#        Semua isi akan dicetak tanpa dibatasi."""
#     blob_list = list(blob_container.list_blobs(name_starts_with=prefix))
#     print(f"🔎 Found {len(blob_list)} blobs with prefix '{prefix}'\n")

#     for b in blob_list:
#         print(f"\n=== 📄 File: {b.name} ===")
#         print(b)
#         # Step 1: Download binary file
#         blob_client = blob_container.get_blob_client(b.name)
#         content_bytes = blob_client.download_blob().readall()
#         print(f"✅ Downloaded {len(content_bytes)} bytes")

#         # Step 2: Extract text + structure
#         doc_data = _extract_text_with_docint(content_bytes)
#         print("\n--- 📝 Extracted Document Data ---")
#         print(f"Sections: {len(doc_data['sections'])}")
#         print(f"Tables: {len(doc_data['raw_tables'])}")
#         print(f"Document structure parts: {len(doc_data['document_structure'])}")

#         # Cetak semua sections dan parts
#         for i, section in enumerate(doc_data["sections"]):
#             print(f"\n[Section {i}] Header: {section['header']}")
#             for j, part in enumerate(section["content_parts"]):
#                 print(f"- Part {j}: {part['content']} (tokens={part['tokens']})")

#         # Step 3: Clean text test (ambil contoh dari section pertama kalau ada)
#         if doc_data["sections"] and doc_data["sections"][0]["content_parts"]:
#             sample_text = doc_data["sections"][0]["content_parts"][0]["content"]
#             print("\n--- 🔧 Clean Text Test ---")
#             print("Before:", sample_text[:500])
#             print("After :", _clean_text(sample_text)[:500])

#         # Step 4: Create intelligent chunks
#         chunks = _create_intelligent_chunks(doc_data)
#         print(f"\n--- 📦 Created {len(chunks)} Chunks ---")
#         for i, ch in enumerate(chunks):
#             print(f"[Chunk {i}] type={ch['type']} tokens={ch['tokens']}")
#             print(ch["content"], "\n")

#         print("=== ✅ Finished Debug for this file ===\n")




# if __name__ == "__main__":
#     with open("debug_output.txt", "w", encoding="utf-8") as f:
#         with contextlib.redirect_stdout(f):
#             debug_process_docs("sop/")

#     print("✅ Debug output saved to debug_output.txt")
