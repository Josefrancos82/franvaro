import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(
    page_title="Frånvaro- & Trendanalys",
    page_icon="📊",
    layout="wide"
)

# File path for persistent local storage
DATA_FILE = "attendance_history.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Initialize database
history = load_data()

st.title("📊 Frånvaro- & Trendanalys (Attendance & Trend Tracker)")
st.markdown("""
Verktyg för skolledning och elevhälsa (EHT) att följa elevers frånvaro månad för månad, upptäcka mönster och identifiera trender enligt **Skollagen (2010:800) 7 kap. 19 a §**.
""")

# Sidebar for global settings & info
st.sidebar.header("⚙️ Inställningar & Gränsvärden")
threshold_yellow = st.sidebar.slider("🟡 Uppmärksamhet (Gult larm %)", min_value=5, max_value=20, value=10)
threshold_red = st.sidebar.slider("🔴 Hög risk (Rött larm %)", min_value=10, max_value=35, value=15)

st.sidebar.markdown("---")
st.sidebar.info("""
**🔒 Dataskydd & GDPR-information:**
• **Rättslig grund:** Skolan har en lagstadgad skyldighet (*Skollag 7 kap. 19 a §*) att följa upp och utreda frånvaro. Behandling av elevens namn och frånvaro är därför laglig (*GDPR art. 6.1 c/e*).
• **Säkerhetskrav:** Vid hantering av fullständiga elevnamn ska appen köras internt på skolans behörighetsskyddade datorer/nätverk. Vid publicering på öppna webbsidor ska anonymiserade elev-ID användas.
""")

# Navigation tabs (3 tabs now, report generator removed)
tab1, tab2, tab3 = st.tabs([
    "📥 1. Registrera Månadsdata",
    "📈 2. Riskanalys & Trender",
    "🔍 3. Lektions- & Mönsteranalys"
])

# --- TAB 1: REGISTRERA MÅNADSDATA ---
with tab1:
    st.header("Registrera ny frånvarorapport")
    st.write("Skriv in eller klistra in månadens frånvaro. Du kan använda elevens fullständiga namn eller elev-ID/kod.")
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        selected_month = st.text_input("Månad/Period (t.ex. 2026-09 eller September)", value="2026-09")
    with col_m2:
        num_rows = st.number_input("Antal elever att registrera", min_value=1, max_value=200, value=5)
        
    st.subheader("Data-inmatning")
    
    # Default template with full names supported
    default_df = pd.DataFrame({
        "Elev_Namn": ["Anna Andersson", "Björn Berg", "Cecilia Ceder", "David Dahl", "Elena Ek"][:num_rows] + [f"Elev {i+1}" for i in range(5, num_rows)],
        "Klass": ["7A" for _ in range(num_rows)],
        "Franvaro_Pct": [5.0, 12.0, 18.5, 3.0, 22.0][:num_rows] + [5.0]*(num_rows-5 if num_rows>5 else 0)
    })
    
    edited_df = st.data_editor(
        default_df,
        num_rows="dynamic",
        column_config={
            "Elev_Namn": st.column_config.TextColumn("Elevens namn / ID", required=True),
            "Klass": st.column_config.TextColumn("Klass", required=True),
            "Franvaro_Pct": st.column_config.NumberColumn("Frånvaro (%)", min_value=0.0, max_value=100.0, format="%.1f %%")
        },
        use_container_width=True
    )
    
    if st.button("💾 Spara månadsdata till historik", type="primary"):
        month_records = edited_df.to_dict(orient="records")
        history[selected_month] = month_records
        save_data(history)
        st.success(f"Data för {selected_month} har sparats i historiken!")

# --- TAB 2: RISKANALYS & TRENDER ---
with tab2:
    st.header("Riskanalys och historisk trendutveckling")
    
    if not history:
        st.warning("Ingen historisk data är registrerad än. Gå till Tab 1 för att lägga till månadsdata.")
    else:
        all_rows = []
        for month, records in history.items():
            for rec in records:
                # Support both Elev_Namn and older Elev_ID keys
                name_key = rec.get("Elev_Namn") or rec.get("Elev_ID") or "Okänd"
                all_rows.append({
                    "Period": month,
                    "Elev_Namn": name_key,
                    "Klass": rec.get("Klass", "-"),
                    "Franvaro_Pct": float(rec["Franvaro_Pct"])
                })
        df_all = pd.DataFrame(all_rows)
        
        months_available = sorted(list(history.keys()))
        selected_view_month = st.selectbox("Välj månad för riskanalys:", months_available, index=len(months_available)-1)
        
        df_month = df_all[df_all["Period"] == selected_view_month].copy()
        
        def assign_status(val):
            if val >= threshold_red:
                return "🔴 Rött larm (Hög risk)"
            elif val >= threshold_yellow:
                return "🟡 Gult larm (Uppmärksamhet)"
            else:
                return "🟢 Normal"
                
        df_month["Status"] = df_month["Franvaro_Pct"].apply(assign_status)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Totalt registrerade elever", len(df_month))
        c2.metric("🟡 Gult larm (>=" + str(threshold_yellow) + "%)", len(df_month[df_month["Status"].str.contains("Gult")]))
        c3.metric("🔴 Rött larm (>=" + str(threshold_red) + "%)", len(df_month[df_month["Status"].str.contains("Rött")]))
        
        st.subheader(f"Elever med oroande frånvaro ({selected_view_month})")
        flagged_df = df_month[df_month["Franvaro_Pct"] >= threshold_yellow].sort_values(by="Franvaro_Pct", ascending=False)
        
        if flagged_df.empty:
            st.success("Inga elever överstiger gränsvärdena för uppmärksamhet denna månad!")
        else:
            st.dataframe(
                flagged_df[["Elev_Namn", "Klass", "Franvaro_Pct", "Status"]],
                use_container_width=True
            )
            
        st.markdown("---")
        st.subheader("📈 Trendutveckling över tid")
        
        student_list = sorted(df_all["Elev_Namn"].unique())
        selected_students = st.multiselect(
            "Välj elever att följa över tid:",
            student_list,
            default=list(flagged_df["Elev_Namn"].unique()) if not flagged_df.empty else student_list[:3]
        )
        
        if selected_students:
            df_trend = df_all[df_all["Elev_Namn"].isin(selected_students)]
            fig = px.line(
                df_trend,
                x="Period",
                y="Franvaro_Pct",
                color="Elev_Namn",
                markers=True,
                labels={"Franvaro_Pct": "Frånvaro (%)", "Period": "Månad", "Elev_Namn": "Elev"},
                title="Frånvarotrend månad för månad"
            )
            fig.add_hline(y=threshold_red, line_dash="dash", line_color="red", annotation_text="Hög risk")
            fig.add_hline(y=threshold_yellow, line_dash="dash", line_color="orange", annotation_text="Uppmärksamhetsgräns")
            st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: LEKTIONS- & MÖNSTERANALYS ---
with tab3:
    st.header("Fördjupad analys av lektions- och veckodagsmönster")
    st.write("Kartlägg om frånvaron har särskilda mönster (t.ex. fredagar, enskilda ämnen eller sista lektionen).")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        pattern_student = st.text_input("Elevens namn / ID:", value="Cecilia Ceder")
        pattern_days = st.multiselect("Särskilt drabbade veckodagar:", ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag"], default=["Måndag", "Fredag"])
    with col_p2:
        pattern_lessons = st.multiselect("Särskilt drabbade lektioner/ämnen:", ["Morgonlektion", "Sista lektionen", "Idrott & Hälsa", "Matematik", "Språk"], default=["Morgonlektion"])
        pattern_type = st.radio("Frånvarons karaktär:", ["Giltig (Sjukdagar)", "Ogiltig (Ströfrånvaro/Smitning)", "Blandad (Giltig & Ogiltig)"])
        
    st.info(f"**Identifierat mönster för {pattern_student}:** Hög koncentration av frånvaro på {', '.join(pattern_days) if pattern_days else 'inga specifika dagar'} samt vid {', '.join(pattern_lessons) if pattern_lessons else 'inga specifika lektioner'}.")
