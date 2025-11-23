# app.py - COMPLETE VERSION WITH ALL FEATURES
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from auth import authenticate
from db import (
    add_patient,
    get_all_patients,
    get_patient_by_id,
    update_patient,
    delete_patient,
    set_patient_anonymized,
    get_logs,
    search_patients,
    delete_old_records,
    get_patients_for_deletion,
    get_patient_count_by_age,
    add_consent_record,
    get_user_consent,
)
from logs import log_action
from privacy import (
    anonymize_name,
    mask_contact,
    encrypt_value,
    decrypt_value,
    FERNET_AVAILABLE,
    initialize_encryption_key,
    validate_name,
    validate_contact,
    validate_diagnosis,
)


# ---------- BASIC CONFIG ----------

st.set_page_config(
    page_title="Mini Hospital Privacy Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize encryption on startup
if FERNET_AVAILABLE:
    initialize_encryption_key()

# ---------- SESSION HELPERS ----------

if "user" not in st.session_state:
    st.session_state.user = None

if "login_time" not in st.session_state:
    st.session_state.login_time = None

if "last_sync" not in st.session_state:
    st.session_state.last_sync = None

if "consent_given" not in st.session_state:
    st.session_state.consent_given = False

if "use_encryption" not in st.session_state:
    st.session_state.use_encryption = FERNET_AVAILABLE


def get_uptime_str():
    if not st.session_state.login_time:
        return "N/A"
    seconds = int(time.time() - st.session_state.login_time)
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours}h {mins}m {secs}s"


# ---------- GDPR CONSENT BANNER ----------

def show_consent_banner():
    """Show GDPR consent banner on first login"""
    user = st.session_state.user
    
    if not user:
        return
    
    # Check if user has already given consent
    consent_record = get_user_consent(user['user_id'])
    
    if consent_record:
        st.session_state.consent_given = True
        return
    
    if st.session_state.consent_given:
        return
    
    # Show consent banner
    st.warning("🔒 **GDPR Data Processing Consent Required**")
    st.info("""
    **We process your personal data in accordance with GDPR regulations.**
    
    By using this system, you consent to:
    - Processing of medical records for healthcare purposes
    - Storage of data for up to 90 days (automatic deletion after)
    - Access by authorized medical staff only
    - Logging of all access activities
    
    You have the right to:
    ✓ Access your data
    ✓ Request data deletion (Right to be Forgotten)
    ✓ Export your data
    """)
    
    col1, col2 = st.columns([1, 5])
    
    with col1:
        if st.button("✅ I Consent", type="primary"):
            st.session_state.consent_given = True
            add_consent_record(user['user_id'], "data_processing")
            log_action(user, "gdpr_consent", "User gave GDPR consent")
            st.success("Consent recorded. Thank you!")
            st.experimental_rerun()
    
    with col2:
        if st.button("❌ I Do Not Consent"):
            st.error("You must consent to use this system. Logging out...")
            time.sleep(2)
            st.session_state.user = None
            st.experimental_rerun()
    
    st.stop()  # Don't show the rest of the dashboard until consent is given


# ---------- PAGES ----------

def show_login_page():
    st.title("🏥 Hospital Management System")
    st.subheader("Privacy-Compliant & GDPR-Ready")

    st.markdown("---")
    st.subheader("🔐 Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary")

    if submit:
        try:
            user = authenticate(username, password)
        except Exception as e:
            st.error(f"Database error: {e}")
            log_action(None, "login_error", f"Exception: {e}")
            return

        if user:
            st.success(f"✅ Welcome, {user['username']} ({user['role']})")

            st.session_state.user = user
            st.session_state.login_time = time.time()
            st.session_state.last_sync = datetime.now()

            log_action(user, "login", "Successful login")
            time.sleep(1)
            st.experimental_rerun()
        else:
            st.error("❌ Invalid username or password")
            log_action(None, "login_failed", f"username={username}")
    
    # Login credentials hint
    with st.expander("💡 Default Login Credentials"):
        st.code("""
Admin:
  Username: admin
  Password: admin123

Doctor:
  Username: tulaib
  Password: tulaib123

Receptionist:
  Username: hammad
  Password: hammad123
        """)


def show_admin_dashboard():
    st.header("🔐 Admin Dashboard")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Patients",
        "✏️ Edit/Delete",
        "📊 Integrity Logs",
        "🗑️ GDPR & Data Retention",
        "💾 Backup & Status"
    ])

    # ---------- TAB 1: FULL PATIENT VIEW + ADD ----------
    with tab1:
        st.subheader("All Patients (Full Access)")

        # Search functionality
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("🔍 Search patients by name or diagnosis", "")
        with col2:
            st.write("")  # spacing
            search_btn = st.button("Search", type="primary")

        try:
            if search_term and search_btn:
                patients = search_patients(search_term)
                st.info(f"Found {len(patients)} matching records")
            else:
                patients = get_all_patients()
            
            st.session_state.last_sync = datetime.now()
            log_action(st.session_state.user, "view_patients_admin")
        except Exception as e:
            st.error(f"Failed to load patients: {e}")
            return

        if patients:
            df = pd.DataFrame(patients)
            
            # Decrypt diagnosis if using encryption
            if st.session_state.use_encryption and FERNET_AVAILABLE:
                df['diagnosis_decrypted'] = df['diagnosis'].apply(
                    lambda x: decrypt_value(x) if x else ""
                )
                # Reorder columns
                cols = ['patient_id', 'name', 'contact', 'diagnosis_decrypted', 
                        'anonymized_name', 'anonymized_contact', 'date_added']
                df = df[cols]
            
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("No patients in the system yet.")

        st.markdown("---")
        st.markdown("### ➕ Add New Patient")
        
        with st.form("add_patient_admin"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Name *")
                contact = st.text_input("Contact (e.g., 123-456-7890) *")
            
            with col2:
                diagnosis = st.text_area("Diagnosis *", height=100)
                encrypt_diag = st.checkbox(
                    "🔒 Encrypt diagnosis (Fernet)", 
                    value=FERNET_AVAILABLE,
                    disabled=not FERNET_AVAILABLE
                )
            
            submitted = st.form_submit_button("Add Patient", type="primary")

        if submitted:
            # Validation
            valid_name, name_err = validate_name(name)
            valid_contact, contact_err = validate_contact(contact)
            valid_diagnosis, diagnosis_err = validate_diagnosis(diagnosis)
            
            if not valid_name:
                st.error(f"❌ Name: {name_err}")
            elif not valid_contact:
                st.error(f"❌ Contact: {contact_err}")
            elif not valid_diagnosis:
                st.error(f"❌ Diagnosis: {diagnosis_err}")
            else:
                try:
                    # Encrypt diagnosis if requested
                    final_diagnosis = diagnosis
                    if encrypt_diag and FERNET_AVAILABLE:
                        final_diagnosis = encrypt_value(diagnosis)
                    
                    add_patient(name, contact, final_diagnosis)
                    log_action(
                        st.session_state.user,
                        "add_patient",
                        f"name={name}, encrypted={encrypt_diag}",
                    )
                    st.success("✅ Patient added successfully.")
                    time.sleep(1)
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Error adding patient: {e}")

        st.markdown("---")
        st.markdown("### 🎭 Anonymize All Patients")
        st.write("Replace real names and contacts with anonymized versions (ANON_XXX, XXX-XXX-XXXX)")

        if st.button("🎭 Anonymize All Now", type="secondary"):
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
                log_action(st.session_state.user, "anonymize_all", f"Anonymized {len(patients)} records")
                st.success(f"✅ All {len(patients)} patient records anonymized.")
                time.sleep(1)
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Anonymization failed: {e}")

    # ---------- TAB 2: EDIT/DELETE PATIENTS ----------
    with tab2:
        st.subheader("✏️ Edit or Delete Patient Records")

        try:
            patients = get_all_patients()
        except Exception as e:
            st.error(f"Failed to load patients: {e}")
            return

        if not patients:
            st.info("No patients to edit.")
            return

        # Patient selector
        patient_options = {
            f"ID {p['patient_id']}: {p['name']} ({p['diagnosis'][:30]}...)": p['patient_id']
            for p in patients
        }
        
        selected_label = st.selectbox("Select patient to edit/delete:", list(patient_options.keys()))
        selected_id = patient_options[selected_label]

        # Get patient details
        patient = get_patient_by_id(selected_id)
        
        if not patient:
            st.error("Patient not found")
            return

        st.markdown("---")
        st.markdown("### Current Details:")
        
        # Decrypt diagnosis if encrypted
        display_diagnosis = patient['diagnosis']
        if st.session_state.use_encryption and FERNET_AVAILABLE:
            try:
                display_diagnosis = decrypt_value(patient['diagnosis'])
            except:
                pass
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Name:** {patient['name']}")
            st.write(f"**Contact:** {patient['contact']}")
        with col2:
            st.write(f"**Diagnosis:** {display_diagnosis}")
            st.write(f"**Date Added:** {patient['date_added']}")

        st.markdown("---")
        st.markdown("### ✏️ Edit Patient")

        with st.form("edit_patient_form"):
            new_name = st.text_input("Name", value=patient['name'])
            new_contact = st.text_input("Contact", value=patient['contact'])
            new_diagnosis = st.text_area("Diagnosis", value=display_diagnosis, height=100)
            
            col1, col2 = st.columns(2)
            with col1:
                update_btn = st.form_submit_button("💾 Update Patient", type="primary")
            with col2:
                # Delete button (separate form)
                pass

        if update_btn:
            # Validation
            valid_name, name_err = validate_name(new_name)
            valid_contact, contact_err = validate_contact(new_contact)
            valid_diagnosis, diagnosis_err = validate_diagnosis(new_diagnosis)
            
            if not valid_name:
                st.error(f"❌ {name_err}")
            elif not valid_contact:
                st.error(f"❌ {contact_err}")
            elif not valid_diagnosis:
                st.error(f"❌ {diagnosis_err}")
            else:
                try:
                    # Encrypt if needed
                    final_diagnosis = new_diagnosis
                    if st.session_state.use_encryption and FERNET_AVAILABLE:
                        final_diagnosis = encrypt_value(new_diagnosis)
                    
                    update_patient(selected_id, new_name, new_contact, final_diagnosis)
                    log_action(
                        st.session_state.user,
                        "update_patient",
                        f"patient_id={selected_id}",
                    )
                    st.success("✅ Patient updated successfully!")
                    time.sleep(1)
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Error updating patient: {e}")

        st.markdown("---")
        st.markdown("### 🗑️ Delete Patient (GDPR Right to Erasure)")
        st.warning("⚠️ This action cannot be undone!")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🗑️ Delete Patient", type="secondary"):
                st.session_state.confirm_delete = True
        
        if st.session_state.get('confirm_delete', False):
            with col2:
                if st.button("✅ Confirm Delete", type="primary"):
                    try:
                        delete_patient(selected_id)
                        log_action(
                            st.session_state.user,
                            "delete_patient",
                            f"patient_id={selected_id}, name={patient['name']} (GDPR erasure)",
                        )
                        st.success("✅ Patient deleted successfully!")
                        st.session_state.confirm_delete = False
                        time.sleep(1)
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"❌ Error deleting patient: {e}")
            
            with col3:
                if st.button("❌ Cancel"):
                    st.session_state.confirm_delete = False
                    st.experimental_rerun()

    # ---------- TAB 3: INTEGRITY LOGS ----------
    with tab3:
        st.subheader("📊 Integrity Audit Log")

        col1, col2 = st.columns([3, 1])
        with col1:
            log_limit = st.slider("Number of logs to display:", 10, 500, 100)
        with col2:
            if st.button("🔄 Refresh Logs"):
                st.experimental_rerun()

        try:
            logs_data = get_logs(limit=log_limit)
        except Exception as e:
            st.error(f"Failed to load logs: {e}")
            return

        if logs_data:
            df_logs = pd.DataFrame(logs_data)
            
            # Color code by action
            st.dataframe(
                df_logs,
                use_container_width=True,
                height=500
            )
            
            # Summary stats
            st.markdown("---")
            st.markdown("### 📈 Log Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Actions", len(df_logs))
            with col2:
                login_count = len(df_logs[df_logs['action'] == 'login'])
                st.metric("Login Events", login_count)
            with col3:
                add_count = len(df_logs[df_logs['action'] == 'add_patient'])
                st.metric("Patients Added", add_count)
            
        else:
            st.info("No log entries yet.")

    # ---------- TAB 4: GDPR & DATA RETENTION ----------
    with tab4:
        st.subheader("🗑️ GDPR Compliance & Data Retention")

        # Data retention policy
        st.markdown("### 📅 Data Retention Policy")
        st.info("""
        **GDPR Compliance:** Patient records are automatically deleted after a specified retention period.
        
        **Current Policy:** Records older than 90 days are eligible for deletion.
        """)

        # Show patient age distribution
        try:
            age_stats = get_patient_count_by_age()
            if age_stats:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Records", age_stats['total'])
                with col2:
                    st.metric("< 30 days", age_stats['last_30_days'])
                with col3:
                    st.metric("< 60 days", age_stats['last_60_days'])
                with col4:
                    st.metric("< 90 days", age_stats['last_90_days'])
        except Exception as e:
            st.warning(f"Could not load statistics: {e}")

        st.markdown("---")
        
        # Show records eligible for deletion
        st.markdown("### 🗑️ Records Eligible for Deletion (>90 days old)")
        
        try:
            old_patients = get_patients_for_deletion(days=90)
            if old_patients:
                st.warning(f"⚠️ Found {len(old_patients)} records older than 90 days")
                df_old = pd.DataFrame(old_patients)
                st.dataframe(df_old, use_container_width=True)
                
                st.markdown("---")
                if st.button("🗑️ Delete Old Records (>90 days)", type="secondary"):
                    try:
                        deleted_count = delete_old_records(days=90)
                        log_action(
                            st.session_state.user,
                            "gdpr_data_retention",
                            f"Deleted {deleted_count} old records (>90 days)",
                        )
                        st.success(f"✅ Deleted {deleted_count} old records")
                        time.sleep(2)
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"❌ Error deleting records: {e}")
            else:
                st.success("✅ No records older than 90 days. All data is within retention policy.")
        except Exception as e:
            st.error(f"Failed to check old records: {e}")

    # ---------- TAB 5: BACKUP & STATUS ----------
    with tab5:
        st.subheader("💾 Backup & System Status")

        # Backup: download CSV of patients
        try:
            patients = get_all_patients()
        except Exception as e:
            st.error(f"Failed to load patients for backup: {e}")
            patients = []

        if patients:
            df = pd.DataFrame(patients)
            
            # Decrypt diagnoses for backup if encrypted
            if st.session_state.use_encryption and FERNET_AVAILABLE:
                df['diagnosis'] = df['diagnosis'].apply(
                    lambda x: decrypt_value(x) if x else ""
                )
            
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Patients CSV (Backup)",
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
        st.markdown("### 📊 System Status")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("System Uptime", get_uptime_str())
        
        with col2:
            last_sync = (
                st.session_state.last_sync.strftime("%Y-%m-%d %H:%M:%S")
                if st.session_state.last_sync
                else "N/A"
            )
            st.write("**Last Sync:**")
            st.write(last_sync)
        
        with col3:
            encryption_status = "✅ Enabled" if FERNET_AVAILABLE else "❌ Disabled"
            st.write("**Encryption:**")
            st.write(encryption_status)


def show_doctor_dashboard():
    st.header("🩺 Doctor Dashboard")
    st.info("**Privacy Note:** You can only view anonymized patient data")

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

    simplified = []
    for p in patients:
        # If patient is anonymized, hide diagnosis too
        if p["anonymized_name"]:  # Record is anonymized
            display_diagnosis = "***CONFIDENTIAL - ANONYMIZED***"
        else:
            # Decrypt if needed
            display_diagnosis = p["diagnosis"]
            if st.session_state.use_encryption and FERNET_AVAILABLE:
                try:
                    display_diagnosis = decrypt_value(p["diagnosis"])
                except:
                    pass
        
        simplified.append({
            "patient_id": p["patient_id"],
            "anonymized_name": p["anonymized_name"] or "NOT_ANONYMIZED",
            "anonymized_contact": p["anonymized_contact"] or "NOT_ANONYMIZED",
            "diagnosis": display_diagnosis,  # ← Hidden if anonymized
            "date_added": p["date_added"],
        })

    df = pd.DataFrame(simplified)
    st.dataframe(df, use_container_width=True, height=500)


def show_receptionist_dashboard():
    st.header("📋 Receptionist Dashboard")

    st.info("**Privacy Note:** You can add/edit records but cannot view sensitive data (names/contacts)")

    # Add patient form
    st.markdown("### ➕ Add New Patient")

    with st.form("add_patient_recep"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name (you won't see this later) *")
            contact = st.text_input("Contact *")
        
        with col2:
            diagnosis = st.text_area("Diagnosis *", height=100)
        
        submitted = st.form_submit_button("Add Patient", type="primary")

    if submitted:
        # Validation
        valid_name, name_err = validate_name(name)
        valid_contact, contact_err = validate_contact(contact)
        valid_diagnosis, diagnosis_err = validate_diagnosis(diagnosis)
        
        if not valid_name:
            st.error(f"❌ {name_err}")
        elif not valid_contact:
            st.error(f"❌ {contact_err}")
        elif not valid_diagnosis:
            st.error(f"❌ {diagnosis_err}")
        else:
            try:
                # Encrypt if available
                final_diagnosis = diagnosis
                if st.session_state.use_encryption and FERNET_AVAILABLE:
                    final_diagnosis = encrypt_value(diagnosis)
                
                add_patient(name, contact, final_diagnosis)
                log_action(
                    st.session_state.user,
                    "add_patient",
                    f"name_length={len(name)} chars",
                )
                st.success("✅ Patient added successfully!")
                time.sleep(1)
                st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Error adding patient: {e}")

    # Show only NON sensitive data
    st.markdown("---")
    st.markdown("### 📋 Patients (Limited View)")

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

    # Decrypt diagnosis if encrypted
    limited_rows = []
    for p in patients:
        display_diagnosis = p["diagnosis"]
        if st.session_state.use_encryption and FERNET_AVAILABLE:
            try:
                display_diagnosis = decrypt_value(p["diagnosis"])
            except:
                pass
        
        limited_rows.append({
            "patient_id": p["patient_id"],
            "diagnosis": display_diagnosis,
            "date_added": p["date_added"],
        })

    df = pd.DataFrame(limited_rows)
    st.dataframe(df, use_container_width=True, height=400)
    
    st.metric("Total Patients", len(patients))


# ---------- MAIN ----------

def main():
    user = st.session_state.user

    if not user:
        show_login_page()
        return

    # Check GDPR consent
    show_consent_banner()

    # Sidebar with role and logout
    with st.sidebar:
        st.markdown("## 👤 User Info")
        st.write(f"**Username:** {user['username']}")
        st.write(f"**Role:** {user['role'].upper()}")
        st.write(f"**Session Uptime:** {get_uptime_str()}")
        
        st.markdown("---")
        
        # System info
        st.markdown("## ⚙️ System Info")
        encryption_icon = "🔒" if FERNET_AVAILABLE else "🔓"
        st.write(f"{encryption_icon} **Encryption:** {'Active' if FERNET_AVAILABLE else 'Unavailable'}")
        
        consent_icon = "✅" if st.session_state.consent_given else "⏳"
        st.write(f"{consent_icon} **GDPR Consent:** {'Given' if st.session_state.consent_given else 'Pending'}")
        
        st.markdown("---")

        if st.button("🚪 Logout", type="primary", use_container_width=True):
            log_action(user, "logout")
            st.session_state.user = None
            st.session_state.login_time = None
            st.session_state.last_sync = None
            st.session_state.consent_given = False
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