from sklearn.feature_extraction.text import TfidfVectorizer
import streamlit as st
from pypdf import PdfReader
import faiss
import re
import tempfile
import numpy as np


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
        q_vec = st.session_state.vectorizer.transform([query]).toarray().astype("float32")

        D, I = st.session_state.index.search(q_vec, k=3)

        st.markdown("### Relevant Policy Sections")

        results = []
        for idx in I[0]:
            results.append(st.session_state.chunks[idx])

        for r in results:
            st.success(r)

        answer = f"""Based on the policy document:

{results[0]}

This section best answers your question:
{query}
"""
        st.write(answer)