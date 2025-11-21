# app.py
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from auth import authenticate
from db import (
    add_patient,
    get_all_patients,
    set_patient_anonymized,
    get_logs,
)
from logs import log_action
from privacy import anonymize_name, mask_contact


# ---------- BASIC CONFIG ----------

st.set_page_config(
    page_title="Mini Hospital Privacy Dashboard",
    layout="wide"
)


# ---------- SESSION HELPERS ----------

if "user" not in st.session_state:
    st.session_state.user = None

if "login_time" not in st.session_state:
    st.session_state.login_time = None

if "last_sync" not in st.session_state:
    st.session_state.last_sync = None


def get_uptime_str():
    if not st.session_state.login_time:
        return "N/A"
    seconds = int(time.time() - st.session_state.login_time)
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours}h {mins}m {secs}s"


# ---------- PAGES ----------

def show_login_page():
    st.title("🏥 Hospital Management System (Privacy & CIA)")

    st.subheader("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        try:
            user = authenticate(username, password)
        except Exception as e:
            st.error(f"Database error: {e}")
            log_action(None, "login_error", f"Exception: {e}")
            return

        if user:
            st.success(f"Welcome, {user['username']} ({user['role']})")

            st.session_state.user = user
            st.session_state.login_time = time.time()
            st.session_state.last_sync = datetime.now()

            log_action(user, "login", "Successful login")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")
            log_action(None, "login_failed", f"username={username}")


def show_admin_dashboard():
    st.header("🔐 Admin Dashboard")

    tab1, tab2, tab3 = st.tabs(
        ["Patients (Full Access)", "Integrity Audit Logs", "Backup / Status"]
    )

    # ---------- TAB 1: FULL PATIENT VIEW + ANONYMIZE ----------
    with tab1:
        st.subheader("All Patients (Raw & Anonymized)")

        try:
            patients = get_all_patients()
            st.session_state.last_sync = datetime.now()
            log_action(st.session_state.user, "view_patients_admin")
        except Exception as e:
            st.error(f"Failed to load patients: {e}")
            return

        if patients:
            df = pd.DataFrame(patients)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No patients in the system yet.")

        st.markdown("### Add New Patient")
        with st.form("add_patient_admin"):
            name = st.text_input("Name")
            contact = st.text_input("Contact")
            diagnosis = st.text_input("Diagnosis")
            submitted = st.form_submit_button("Add patient")

        if submitted:
            if not name or not contact or not diagnosis:
                st.warning("Please fill all fields.")
            else:
                try:
                    add_patient(name, contact, diagnosis)
                    log_action(
                        st.session_state.user,
                        "add_patient",
                        f"name={name}, contact={contact}",
                    )
                    st.success("Patient added.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error adding patient: {e}")

        st.markdown("### Anonymize All Patients")

        if st.button("Anonymize now"):
            try:
                patients = get_all_patients()
                for p in patients:
                    anon_name = anonymize_name(p["name"])
                    masked_contact = mask_contact(p["contact"])
                    set_patient_anonymized(
                        p["patient_id"],
                        anon_name,
                        masked_contact,
                    )
                log_action(st.session_state.user, "anonymize_all")
                st.success("All patient records anonymized.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Anonymization failed: {e}")

    # ---------- TAB 2: INTEGRITY LOGS ----------
    with tab2:
        st.subheader("Integrity Audit Log")

        try:
            logs_data = get_logs()
        except Exception as e:
            st.error(f"Failed to load logs: {e}")
            return

        if logs_data:
            df_logs = pd.DataFrame(logs_data)
            st.dataframe(df_logs, use_container_width=True)
        else:
            st.info("No log entries yet.")

    # ---------- TAB 3: BACKUP / STATUS ----------
    with tab3:
        st.subheader("Backup & System Status")

        # Backup: download CSV of patients
        try:
            patients = get_all_patients()
        except Exception as e:
            st.error(f"Failed to load patients for backup: {e}")
            patients = []

        if patients:
            df = pd.DataFrame(patients)
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download patients as CSV (Backup)",
                data=csv_bytes,
                file_name=f"patients_backup_{datetime.now().date()}.csv",
                mime="text/csv",
            )
            log_action(
                st.session_state.user,
                "export_csv",
                "Patients CSV downloaded",
            )
        else:
            st.info("No patients available for backup.")

        st.markdown("---")
        st.write(f"**System Uptime:** {get_uptime_str()}")
        last_sync = (
            st.session_state.last_sync.strftime("%Y-%m-%d %H:%M:%S")
            if st.session_state.last_sync
            else "N/A"
        )
        st.write(f"**Last Synchronization Time:** {last_sync}")


def show_doctor_dashboard():
    st.header("🩺 Doctor Dashboard")

    st.write(
        "You can see only **anonymized** patient data "
        "(no real names or contact numbers)."
    )

    try:
        patients = get_all_patients()
        st.session_state.last_sync = datetime.now()
        log_action(st.session_state.user, "view_patients_doctor")
    except Exception as e:
        st.error(f"Failed to load patients: {e}")
        return

    if not patients:
        st.info("No patients available.")
        return

    # Only anonymized fields + diagnosis + date
    simplified = []
    for p in patients:
        simplified.append(
            {
                "patient_id": p["patient_id"],
                "anonymized_name": p["anonymized_name"] or "NOT_ANONYMIZED",
                "anonymized_contact": p["anonymized_contact"]
                or "NOT_ANONYMIZED",
                "diagnosis": p["diagnosis"],
                "date_added": p["date_added"],
            }
        )

    df = pd.DataFrame(simplified)
    st.dataframe(df, use_container_width=True)


def show_receptionist_dashboard():
    st.header("📋 Receptionist Dashboard")

    st.write(
        "You can **add/edit patient records**, but you **cannot see** "
        "real names or contacts."
    )

    # Add patient form
    st.markdown("### Add New Patient")

    with st.form("add_patient_recep"):
        name = st.text_input("Name (you enter, but won't see later)")
        contact = st.text_input("Contact")
        diagnosis = st.text_input("Diagnosis")
        submitted = st.form_submit_button("Add patient")

    if submitted:
        if not name or not contact or not diagnosis:
            st.warning("Please fill all fields.")
        else:
            try:
                add_patient(name, contact, diagnosis)
                log_action(
                    st.session_state.user,
                    "add_patient",
                    f"name_entered={len(name)} chars",
                )
                st.success("Patient added successfully.")
            except Exception as e:
                st.error(f"Error adding patient: {e}")

    # Show only NON sensitive data
    st.markdown("### Patients (Limited View)")

    try:
        patients = get_all_patients()
        st.session_state.last_sync = datetime.now()
        log_action(st.session_state.user, "view_patients_recep")
    except Exception as e:
        st.error(f"Failed to load patients: {e}")
        return

    if not patients:
        st.info("No patients yet.")
        return

    limited_rows = []
    for p in patients:
        limited_rows.append(
            {
                "patient_id": p["patient_id"],
                "diagnosis": p["diagnosis"],
                "date_added": p["date_added"],
            }
        )

    df = pd.DataFrame(limited_rows)
    st.dataframe(df, use_container_width=True)


# ---------- MAIN ----------

def main():
    user = st.session_state.user

    if not user:
        show_login_page()
        return

    # Sidebar with role and logout
    with st.sidebar:
        st.markdown("## User Info")
        st.write(f"**Username:** {user['username']}")
        st.write(f"**Role:** {user['role']}")
        st.write(f"**Uptime:** {get_uptime_str()}")

        if st.button("Logout"):
            log_action(user, "logout")
            st.session_state.user = None
            st.session_state.login_time = None
            st.session_state.last_sync = None
            st.experimental_rerun()

    # Role-based views
    role = user["role"]

    if role == "admin":
        show_admin_dashboard()
    elif role == "doctor":
        show_doctor_dashboard()
    elif role == "receptionist":
        show_receptionist_dashboard()
    else:
        st.error(f"Unknown role: {role}")


if __name__ == "__main__":
    main()
