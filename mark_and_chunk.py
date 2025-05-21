import langchain 
import langchain_community
import langchain_ollama
from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter, MarkdownTextSplitter
from langchain_text_splitters.character import CharacterTextSplitter
from qdrant_client import QdrantClient
import os 
import fitz 
from langchain.vectorstores import Qdrant
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
from tqdm import tqdm 
from qdrant_client.models import VectorParams

# project-specific imports 
from custom_header_detection import mark_sections, extract_text_and_tables # CUSTOM HEADER EXTRACTION HEURISTIC 
from pymu4llm_custom_header_detection import get_normal_font_size, custom_header_detection, custom_hdr_info # CUSTOM HEURISTIC + PYMU4LLM 
import pymupdf4llm # FOR DEFAULT MARKDOWN GENERATION 
# -------------------------

FOLDER_PATH = "pdfs/"
PDF_PATHS = [os.path.join(FOLDER_PATH, pdf_name) for pdf_name in os.listdir(FOLDER_PATH)]
character_splitter = CharacterTextSplitter(separator="\n", chunk_size =1000 ,chunk_overlap=100)
markdown_header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("##", "Header 2")])
markdown_text_splitter = MarkdownTextSplitter()

client = QdrantClient(host="localhost", port=6333)


# Initialize MiniLM embeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


COLLECTIONS = [
    "custom_markdown_detection",
    "custom_header_detection_pymupdf4llm",
    "default_header_detection_pymupdf4llm", 
    "character_splitter"
]

for collection_name in COLLECTIONS:
    client.create_collection(collection_name=collection_name, vectors_config=VectorParams(size=384, distance="Cosine")) 


for pdf in tqdm(PDF_PATHS):
    # CUSTOM HEADER DETECTION ------------------------------ 
    try: 
        custom_markdown_text = mark_sections(extract_text_and_tables(pdf))

        chunks = markdown_header_splitter.split_text(custom_markdown_text)

        qdrant_vs = Qdrant(client=client, collection_name="custom_markdown_detection", embeddings=embeddings)
        qdrant_vs.add_documents(chunks)
    except Exception as e: 
        print(f"Unable to process document : {pdf}, reason: {e} ")
        continue

    # --------------------------------------------------------


    # CUSTOM IMPLEMENTED HEADER DETECTION FOR PYMU4LLLM ------
    try:
        doc = fitz.open(pdf)
        markdown_lines = []
        
        for page in doc:
            normal_font_size = get_normal_font_size(page)
            
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        hdr_prefix = custom_header_detection(span, page, normal_font_size)
                        text = span['text']
                        if hdr_prefix:
                            line_text += f"{hdr_prefix}{text}\n"
                        else:
                            line_text += text
                    markdown_lines.append(line_text)
            markdown_lines.append("\n")  # page break for readability
        
        custom_pymupdf_markdown = "\n".join(markdown_lines)
        
        # Chunk & store pymupdf4llm custom detection markdown
        chunks = markdown_header_splitter.split_text(custom_pymupdf_markdown)
        
        qdrant_vs_pymupdf = Qdrant(client=client, collection_name="custom_header_detection_pymupdf4llm", embeddings=embeddings)
        qdrant_vs_pymupdf.add_documents(chunks)
        # --------------------------------------------------------
    except Exception as e:
        print(f"Unable to process document {pdf}, reason: {e} ")
        continue
    # DEFAULT MYPDF -------------------------------------------
    
    default_mypdf_markdown = pymupdf4llm.to_markdown(pdf)
    chunks = markdown_text_splitter.split_text(default_mypdf_markdown)

    docs = [Document(page_content=chunk, metadata={"source_pdf": pdf}) for chunk in chunks]
    
    qdrant_default_mypdf = Qdrant(client=client, collection_name="default_header_detection_pymupdf4llm", embeddings=embeddings)
    qdrant_default_mypdf.add_documents(docs)
    # ----------------------------------------------------------


    # CHARACTER SPLITTING ---------------------

    raw_text = ""
    with fitz.open(pdf) as doc:
        for page in doc:
            raw_text += page.get_text()
            raw_text += "\n"

    char_chunks = character_splitter.split_text(raw_text)
    docs = [Document(page_content=chunk, metadata={"source_pdf": pdf}) for chunk in char_chunks]
    qdrant_vs_char = Qdrant(client=client, collection_name="character_splitter", embeddings=embeddings)
    qdrant_vs_char.add_documents(docs)

    #-----------------------------------------