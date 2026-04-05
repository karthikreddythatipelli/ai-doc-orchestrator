import streamlit as st
import os
import hashlib
import requests
import google.generativeai as genai
from PyPDF2 import PdfReader
import docx

# ----------------------------
# API KEY (LOCAL + CLOUD)
# ----------------------------
if "GOOGLE_API_KEY" in st.secrets:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("❌ GOOGLE_API_KEY not set")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ----------------------------
# WEBHOOK (LOCAL + CLOUD)
# ----------------------------
if "WEBHOOK_URL" in st.secrets:
    WEBHOOK_URL = st.secrets["WEBHOOK_URL"]
else:
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")

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
# NEW: STRUCTURED JSON EXTRACTION
# ----------------------------
def extract_structured_json(text):
    prompt = f"""
    Extract structured JSON from the document.
    Include:
    - risk_level (Low, Medium, High)
    - important_entities
    - summary_points

    Document:
    {text[:5000]}
    """
    return safe_generate(prompt)

# ----------------------------
# STREAMLIT UI
# ----------------------------
st.set_page_config(page_title="AI Document Orchestrator", layout="wide")

st.title("📄 AI-Powered Document Orchestrator")

uploaded_file = st.file_uploader("Upload document", type=["pdf","docx","txt"])

# ----------------------------
# FIX FILE CHANGE BUG
# ----------------------------
if uploaded_file:
    file_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()

    if "file_hash" not in st.session_state or st.session_state.file_hash != file_hash:
        st.session_state.clear()
        st.session_state.file_hash = file_hash

        text = extract_text(uploaded_file)

        if text:
            st.session_state["document_text"] = text
            st.success("✅ New document processed!")
        else:
            st.error("❌ Unsupported file")

# ----------------------------
# MAIN APP
# ----------------------------
if "document_text" in st.session_state:
    text = st.session_state["document_text"]

    st.text_area("Preview", text[:2000], height=200)

    # ----------------------------
    # BASIC FEATURES
    # ----------------------------
    if st.button("📌 Summarize"):
        st.session_state["summary"] = summarize_text(text)

    if st.button("🔑 Key Points"):
        st.session_state["points"] = extract_key_points(text)

    if st.button("📦 Extract JSON"):
        st.session_state["json_data"] = extract_structured_json(text)

    if "summary" in st.session_state:
        st.subheader("Summary")
        st.write(st.session_state["summary"])

    if "points" in st.session_state:
        st.subheader("Key Points")
        st.write(st.session_state["points"])

    if "json_data" in st.session_state:
        st.subheader("📦 Structured Data (JSON)")
        st.write(st.session_state["json_data"])

    # ----------------------------
    # Q&A
    # ----------------------------
    q = st.text_input("Ask question")

    if st.button("Ask"):
        if q:
            st.session_state["question"] = q
            st.session_state["answer"] = ask_question(text, q)
        else:
            st.warning("Enter a question")

    if "answer" in st.session_state:
        st.write("### Answer")
        st.write(st.session_state["answer"])

    # ----------------------------
    # NEW: CONDITIONAL EMAIL TRIGGER
    # ----------------------------
    st.subheader("🚨 Send Alert Mail")

    email = st.text_input("Enter Recipient Email ID")

    if st.button("Send Alert Mail"):
        if email and "summary" in st.session_state:

            payload = {
                "email": email,
                "document_text": st.session_state.get("document_text", ""),
                "summary": st.session_state.get("summary", ""),
                "question": st.session_state.get("question", ""),
                "answer": st.session_state.get("answer", ""),
                "json_data": st.session_state.get("json_data", "")
            }

            try:
                response = requests.post(WEBHOOK_URL, json=payload, timeout=15)

                if response.status_code == 200:
                    data = response.json()

                    st.session_state["final_answer"] = data.get("final_answer")
                    st.session_state["email_body"] = data.get("email_body")
                    st.session_state["status"] = data.get("status")

                else:
                    st.error("❌ Webhook failed")

            except Exception as e:
                st.error(f"❌ Error: {e}")

        else:
            st.warning("⚠️ Enter email and generate summary first")

    # ----------------------------
    # DISPLAY FINAL OUTPUT
    # ----------------------------
    if "final_answer" in st.session_state:
        st.subheader("🧠 Final Analytical Answer")
        st.write(st.session_state["final_answer"])

    if "email_body" in st.session_state:
        st.subheader("📧 Generated Email Body")
        st.write(st.session_state["email_body"])

    if "status" in st.session_state:
        st.subheader("📊 Email Automation Status")
        st.success(st.session_state["status"])

else:
    st.info("Upload a document to get started.")