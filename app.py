from sklearn.feature_extraction.text import TfidfVectorizer
import streamlit as st
from pypdf import PdfReader
from google import genai
import faiss
import re
import tempfile
import numpy as np
import time

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="Smart RAG System", layout="wide")
st.title("Smart RAG (Clean Retrieval System)")


def load_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        content = page.extract_text()
        if content:
            text += content
    return text


def split_text(text):
    chunks = re.split(r"\n(?=[A-Z][A-Za-z &]+(\n|:))", text)
    cleaned = []
    for c in chunks:
        c = c.strip()
        if len(c) > 80:
            cleaned.append(c)
    return cleaned


uploaded_file = st.file_uploader("Upload Business Policy PDF", type="pdf")

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.read())
        file_path = tmp.name

    text = load_pdf(file_path)
    chunks = split_text(text)

    if len(chunks) == 0:
        st.error("No valid text chunks found in PDF")
    else:
        st.success(f"Document loaded with {len(chunks)} clean sections")

        vectorizer = TfidfVectorizer(stop_words="english")
        X = vectorizer.fit_transform(chunks).toarray().astype("float32")

        index = faiss.IndexFlatL2(X.shape[1])
        index.add(X)

        st.session_state.chunks = chunks
        st.session_state.vectorizer = vectorizer
        st.session_state.index = index

        st.info("RAG System Ready ✅")


query = st.text_input("Ask a Question")

if query:
    if "index" not in st.session_state:
        st.warning("Please upload a PDF first.")
    else:
        q_vec = st.session_state.vectorizer.transform(
            [query]
        ).toarray().astype("float32")

        D, I = st.session_state.index.search(q_vec, k=3)

        st.markdown("### Relevant Policy Sections")

        results = []

        for idx in I[0]:
            results.append(st.session_state.chunks[idx])

        for r in results:
            st.success(r)

        # Combine retrieved sections into context
        context = "\n\n".join(results)

        # Send retrieved context + question to Gemini
        prompt = f"""
You are a document question-answering assistant.

Answer the user's question using only the information provided
in the document context below.

If the answer is not available in the context, clearly say:
"I could not find this information in the document."

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{query}

ANSWER:
"""

max_retries = 3
response = None

for attempt in range(max_retries):
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )
        break

    except Exception as e:
        if attempt < max_retries - 1:
            time.sleep(2)
        else:
            st.warning(
                "The AI service is temporarily busy. "
                "Please try your question again in a moment."
            )

if response is not None:
    st.markdown("### AI Generated Answer")
    st.write(response.text)