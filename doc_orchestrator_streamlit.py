
import streamlit as st
import os
import google.generativeai as genai
from PyPDF2 import PdfReader
import docx
import requests

# ----------------------------
# CONFIGURE GEMINI (SAFE)
# ----------------------------
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("❌ GOOGLE_API_KEY not set")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ----------------------------
# FILE PROCESSING
# ----------------------------

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text(file):
    if file.type == "application/pdf":
        return extract_text_from_pdf(file)
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(file)
    elif file.type == "text/plain":
        return file.read().decode("utf-8")
    return None

# ----------------------------
# GEMINI FUNCTIONS
# ----------------------------

def safe_generate(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text if response and hasattr(response, "text") else "No response."
    except Exception as e:
        return f"Error: {str(e)}"

def summarize_text(text):
    return safe_generate(f"Summarize this document:\n\n{text[:10000]}")

def extract_key_points(text):
    return safe_generate(f"Extract key points:\n\n{text[:10000]}")

def ask_question(text, question):
    return safe_generate(f"Document:\n{text[:10000]}\nQuestion:{question}")

# ----------------------------
# STREAMLIT UI
# ----------------------------

st.set_page_config(page_title="AI Document Orchestrator", layout="wide")

st.title("📄 AI-Powered Document Orchestrator")

uploaded_file = st.file_uploader("Upload document", type=["pdf","docx","txt"])

# Process file once
if uploaded_file and "document_text" not in st.session_state:
    text = extract_text(uploaded_file)
    if text:
        st.session_state["document_text"] = text
        st.success("✅ Document processed!")
    else:
        st.error("❌ Unsupported file")

# ----------------------------
# MAIN APP
# ----------------------------

if "document_text" in st.session_state:
    text = st.session_state["document_text"]

    st.text_area("Preview", text[:2000], height=200)

    # Buttons
    if st.button("📌 Summarize"):
        st.session_state["summary"] = summarize_text(text)

    if st.button("🔑 Key Points"):
        st.session_state["points"] = extract_key_points(text)

    # Outputs
    if "summary" in st.session_state:
        st.subheader("Summary")
        st.write(st.session_state["summary"])

    if "points" in st.session_state:
        st.subheader("Key Points")
        st.write(st.session_state["points"])

    # ----------------------------
    # Q&A
    # ----------------------------
    q = st.text_input("Ask question")

    if st.button("Ask"):
        if q:
            st.session_state["answer"] = ask_question(text, q)
        else:
            st.warning("Enter a question")

    if "answer" in st.session_state:
        st.write("### Answer")
        st.write(st.session_state["answer"])

    # ----------------------------
    # EMAIL (n8n integration)
    # ----------------------------

    st.subheader("📧 Send Summary via Email")

    email = st.text_input("Enter email")

    if st.button("Send Email"):
        if "summary" in st.session_state and email:
            try:
                response = requests.post(
                    "https://karthikreddy3131.app.n8n.cloud/webhook/doc_orchestrator",
                    json={
                        "email": email,
                        "summary": st.session_state["summary"]
                    }
                )

                if response.status_code == 200:
                    st.success("🚀 Email sent successfully!")
                else:
                    st.error(f"❌ Failed: {response.text}")

            except Exception as e:
                st.error(f"❌ Error: {e}")
        else:
            st.warning("⚠️ Generate summary and enter email first")

else:
    st.info("Upload a document to get started.")
