
import streamlit as st
import sqlite3
import pandas as pd
import re
from datetime import date
import requests
import os

DB = "patients.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS patients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        dob TEXT,
        email TEXT,
        glucose REAL,
        haemoglobin REAL,
        cholesterol REAL,
        remarks TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_patient(data):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""INSERT INTO patients
    (full_name,dob,email,glucose,haemoglobin,cholesterol,remarks)
    VALUES (?,?,?,?,?,?,?)""", data)
    conn.commit()
    conn.close()

def get_patients():
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM patients", conn)
    conn.close()
    return df

def update_patient(pid, data):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""UPDATE patients SET
    full_name=?, dob=?, email=?, glucose=?, haemoglobin=?, cholesterol=?, remarks=?
    WHERE id=?""", (*data, pid))
    conn.commit()
    conn.close()

def delete_patient(pid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM patients WHERE id=?", (pid,))
    conn.commit()
    conn.close()

def valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def ai_prediction(glucose, haemoglobin, cholesterol):
    api_key = os.getenv("OPENROUTER_API_KEY")

    prompt = f"""
    Based on:
    Glucose: {glucose}
    Haemoglobin: {haemoglobin}
    Cholesterol: {cholesterol}

    Give a short possible health risk remark in one sentence only.
    """

    if api_key:
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model":"openai/gpt-4o-mini",
                "messages":[{"role":"user","content":prompt}]
            }
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            result = r.json()
            return result["choices"][0]["message"]["content"]
        except:
            pass

    # fallback logic if API key missing
    if glucose > 140:
        return "Possible diabetes risk."
    elif haemoglobin < 12:
        return "Possible low haemoglobin / anaemia risk."
    elif cholesterol > 200:
        return "Possible cholesterol-related risk."
    else:
        return "Values appear within a healthy range."

init_db()

st.title("Health Prediction Application")

menu = ["Add Patient", "View Records", "Update", "Delete"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Add Patient":
    st.subheader("Add Patient")

    full_name = st.text_input("Full Name")
    dob = st.date_input("Date of Birth")
    email = st.text_input("Email Address")
    glucose = st.text_input("Glucose")
    haemoglobin = st.text_input("Haemoglobin")
    cholesterol = st.text_input("Cholesterol")

    if st.button("Predict & Save"):
        if not valid_email(email):
            st.error("Invalid email format")
        elif dob > date.today():
            st.error("DOB cannot be future date")
        else:
            try:
                glucose = float(glucose)
                haemoglobin = float(haemoglobin)
                cholesterol = float(cholesterol)

                remarks = ai_prediction(glucose, haemoglobin, cholesterol)

                add_patient((
                    full_name,
                    str(dob),
                    email,
                    glucose,
                    haemoglobin,
                    cholesterol,
                    remarks
                ))

                st.success("Patient saved successfully")
                st.info(f"AI Remark: {remarks}")

            except:
                st.error("Blood values must be numeric")

elif choice == "View Records":
    st.subheader("Patient Records")
    st.dataframe(get_patients())

elif choice == "Update":
    st.subheader("Update Record")
    df = get_patients()

    if not df.empty:
        pid = st.selectbox("Select Patient ID", df["id"])
        row = df[df["id"] == pid].iloc[0]

        full_name = st.text_input("Full Name", row["full_name"])
        dob = st.date_input("DOB", pd.to_datetime(row["dob"]))
        email = st.text_input("Email", row["email"])
        glucose = st.text_input("Glucose", str(row["glucose"]))
        haemoglobin = st.text_input("Haemoglobin", str(row["haemoglobin"]))
        cholesterol = st.text_input("Cholesterol", str(row["cholesterol"]))

        if st.button("Update"):
            remarks = ai_prediction(float(glucose), float(haemoglobin), float(cholesterol))
            update_patient(pid, (
                full_name,
                str(dob),
                email,
                float(glucose),
                float(haemoglobin),
                float(cholesterol),
                remarks
            ))
            st.success("Updated successfully")

elif choice == "Delete":
    st.subheader("Delete Record")
    df = get_patients()

    if not df.empty:
        pid = st.selectbox("Select ID", df["id"])
        if st.button("Delete"):
            delete_patient(pid)
            st.success("Deleted successfully")
