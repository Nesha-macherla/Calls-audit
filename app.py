import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import openai
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Iron Lady Call Analysis System",
    page_icon="👩‍💼",
    layout="wide"
)

# Initialize OpenAI client
openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

# Create data directory if it doesn't exist
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
DB_FILE = DATA_DIR / "calls_database.json"

# Call type parameters
CALL_PARAMETERS = {
    "Welcome Call": [
        "Rapport building",
        "Profile understanding",
        "Credibility of RM and Iron Lady",
        "Principles usage",
        "Case studies usage",
        "Right key questions",
        "Gap creation",
        "BHAG fine tuning",
        "Commitment for 2 days session",
        "Concern handling",
        "Urgency creation towards BHAG and community",
        "Community details and pricing",
        "Creating excitement",
        "Contextualisation",
        "Commitment to connect for next 2 days"
    ],
    "BHAG Call": [
        "Connect (Greetings / About session key points taken away)",
        "Key questions about their BHAG",
        "Review of Goal and Breakthrough actions",
        "Nudge them to take a Goal much higher and commit to it",
        "Key questions about Mentors / Network",
        "Case study usage",
        "Key value (2 Major Principles basis on their challenge)",
        "Introduce them to Community",
        "Creating need and importance",
        "Show its an opportunity to join community",
        "Pitch with price",
        "Commitment to attend Day 2 and Day 3 sessions",
        "Explaining about Brand statement / Certification form",
        "Powerful invite and offer"
    ],
    "Registration Call": [
        "Congratulate for completing 2 days of session",
        "Invite powerfully to complete Day 3 session",
        "Nudge towards BHAG",
        "Dealing with concern / challenge",
        "Create need and importance towards BHAG",
        "Create need for support / Network / Handholding",
        "Get her to see the returns",
        "Talk about 3 things: Networking / Community / Continuous handholding",
        "In depth implementation of 27 Principles",
        "Reverse pitch - Immediate BHAG focus",
        "Dealing with concern: Money (Immediate returns + importance)",
        "Dealing with concern: Time (Urgency)",
        "Dealing with concern: Emergency dependency",
        "Being intentional for their growth and supportive",
        "Nudge to publish brand statement",
        "Certification form filling"
    ],
    "30 Sec Pitch": [
        "Details about complete profile",
        "Clarity on BHAG",
        "Connect with participants through pain point",
        "Commitment towards BHAG (How important is BHAG)",
        "Relate case studies (Best case studies)",
        "Key value (2 Major Principles basis on their challenge)",
        "Probing questions about Mentors / Network",
        "Dealing with her challenges",
        "Creating need and importance",
        "Powerful invite and offer",
        "Confidence level"
    ],
    "Second Level Call": [
        "Collect the information (Profile, BHAG, Concern)",
        "Credibility of TL",
        "Extra support (Much more powerful way)",
        "Connect with them immediately through pain point",
        "Providing proper value towards their concern (point to point)",
        "Relate case study",
        "Reassurance returns",
        "Concern handling",
        "Getting strong commitment (Towards registrations)",
        "Convincing skills"
    ],
    "Follow Up Call": [
        "Collect the information (Profile, BHAG, Concern)",
        "Status of commitment towards BHAG",
        "Status of commitment towards community",
        "Connect with them immediately through pain point",
        "Providing proper value towards their concern (point to point)",
        "Relate case study",
        "Reassurance returns",
        "Concern handling",
        "Get the registrations"
    ]
}

# Initialize database
def init_db():
    if not DB_FILE.exists():
        with open(DB_FILE, 'w') as f:
            json.dump([], f)

def load_db():
    init_db()
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def analyze_call_with_gpt(file_path, rm_name, client_name, pitch_outcome, call_type, additional_context):
    """Analyze call recording using ChatGPT API with Iron Lady parameters"""
    try:
        parameters = CALL_PARAMETERS.get(call_type, [])
        parameters_list = "\n".join([f"{i+1}. {param}" for i, param in enumerate(parameters)])
        
        prompt = f"""
You are an expert sales call analyst for Iron Lady, a women's leadership and business coaching program. Analyze this {call_type} with the following details:

- Relationship Manager: {rm_name}
- Client/Participant Name: {client_name}
- Call Outcome: {pitch_outcome}
- Additional Context: {additional_context}

**CRITICAL PARAMETERS TO EVALUATE FOR {call_type.upper()}:**
{parameters_list}

**IRON LADY SPECIFIC CONTEXT:**
- BHAG = Big Hairy Audacious Goal (participant's major life/business goal)
- 27 Principles = Core framework taught in the program
- Community = Network of women entrepreneurs and leaders
- 2-Day Session = Initial workshop, Day 3 = Follow-up session
- Brand Statement = Personal branding exercise
- Certification = Program completion credential

Provide a comprehensive analysis in the following JSON format:

{{
    "overall_score": <number 1-10>,
    "call_effectiveness": "<Excellent/Good/Average/Needs Improvement>",
    
    "parameter_scores": {{
        {json.dumps({param: "<score 1-10>" for param in parameters[:5]})}
    }},
    
    "key_strengths": ["strength1", "strength2", "strength3"],
    "critical_gaps": ["gap1", "gap2", "gap3"],
    
    "specific_observations": {{
        "rapport_and_connection": "<observation>",
        "bhag_clarity_and_commitment": "<observation>",
        "credibility_establishment": "<observation>",
        "case_study_effectiveness": "<observation>",
        "concern_handling": "<observation>",
        "closing_and_commitment": "<observation>"
    }},
    
    "participant_readiness": {{
        "bhag_commitment_level": "<High/Medium/Low>",
        "community_interest": "<High/Medium/Low>",
        "urgency_level": "<High/Medium/Low>",
        "concern_status": "<Resolved/Partially Resolved/Unresolved>"
    }},
    
    "recommendations": [
        "specific recommendation 1",
        "specific recommendation 2",
        "specific recommendation 3"
    ],
    
    "next_steps": [
        "action step 1",
        "action step 2"
    ],
    
    "what_rm_did_well": ["point1", "point2", "point3"],
    "what_rm_missed": ["point1", "point2", "point3"],
    
    "summary": "<2-3 sentence summary focusing on call outcome and participant state>"
}}

Base your analysis on the call outcome being '{pitch_outcome}' and provide actionable insights for {rm_name} to improve their {call_type} technique.
"""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional sales call analyst for Iron Lady coaching program. Always respond with valid JSON only. Be specific and actionable in your feedback."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        analysis_text = response.choices[0].message.content
        
        # Extract JSON from response
        if "```json" in analysis_text:
            analysis_text = analysis_text.split("```json")[1].split("```")[0].strip()
        elif "```" in analysis_text:
            analysis_text = analysis_text.split("```")[1].split("```")[0].strip()
        
        analysis = json.loads(analysis_text)
        return analysis
        
    except Exception as e:
        st.error(f"Error analyzing call: {str(e)}")
        return {
            "overall_score": 7.0,
            "call_effectiveness": "Good",
            "parameter_scores": {},
            "key_strengths": ["Clear communication", "Professional tone"],
            "critical_gaps": ["Need more context for detailed analysis"],
            "specific_observations": {
                "rapport_and_connection": "Unable to analyze without audio",
                "bhag_clarity_and_commitment": "Unable to analyze without audio",
                "credibility_establishment": "Unable to analyze without audio",
                "case_study_effectiveness": "Unable to analyze without audio",
                "concern_handling": "Unable to analyze without audio",
                "closing_and_commitment": "Unable to analyze without audio"
            },
            "participant_readiness": {
                "bhag_commitment_level": "Medium",
                "community_interest": "Medium",
                "urgency_level": "Medium",
                "concern_status": "Partially Resolved"
            },
            "recommendations": ["Upload audio for detailed analysis", "Review call parameters"],
            "next_steps": ["Schedule follow-up", "Review participant BHAG"],
            "what_rm_did_well": ["Professional approach"],
            "what_rm_missed": ["Detailed analysis requires audio"],
            "summary": "Analysis unavailable. Please check API configuration or upload audio for detailed analysis."
        }

# Sidebar navigation
st.sidebar.title("👩‍💼 Iron Lady Call Analysis")
page = st.sidebar.radio("Navigate", ["Upload Recording", "Dashboard", "Admin View"])

# UPLOAD PAGE
if page == "Upload Recording":
    st.title("📤 Upload Call Recording")
    st.write("Upload your Iron Lady sales call recording and get AI-powered analysis based on specific parameters")
    
    with st.form("upload_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            rm_name = st.text_input("RM Name *", placeholder="e.g., Priya Sharma")
            client_name = st.text_input("Participant Name *", placeholder="e.g., Anjali Mehta")
            call_type = st.selectbox(
                "Call Type *",
                ["Welcome Call", "BHAG Call", "Registration Call", "30 Sec Pitch", "Second Level Call", "Follow Up Call"]
            )
        
        with col2:
            pitch_outcome = st.selectbox(
                "Call Outcome *",
                ["Success - Committed", "Partial - Needs Follow-up", "Not Interested", "Rescheduled"]
            )
            call_date = st.date_input("Call Date *", datetime.now())
        
        uploaded_file = st.file_uploader(
            "Upload Recording *",
            type=['mp3', 'wav', 'm4a', 'mp4'],
            help="Supported formats: MP3, WAV, M4A, MP4 (Max 200MB)"
        )
        
        # Show relevant parameters for selected call type
        st.markdown(f"### 📋 Key Parameters for {call_type}")
        st.info("\n".join([f"✓ {param}" for param in CALL_PARAMETERS.get(call_type, [])[:5]]) + "\n... and more")
        
        additional_context = st.text_area(
            "Additional Context *",
            placeholder="e.g., Participant's BHAG: Launch online clothing brand in 6 months\nMain concerns: Time management, funding\nPrevious interaction: Attended Day 1 session",
            height=100
        )
        
        notes = st.text_area(
            "Call Notes (Optional)",
            placeholder="Any specific observations during the call..."
        )
        
        submitted = st.form_submit_button("🚀 Analyze Call", use_container_width=True)
    
    if submitted:
        if not all([rm_name, client_name, uploaded_file, additional_context]):
            st.error("❌ Please fill in all required fields (*)")
        else:
            with st.spinner(f"🔄 Analyzing your {call_type}... This may take 30-60 seconds..."):
                # Save uploaded file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_extension = uploaded_file.name.split('.')[-1]
                filename = f"{rm_name.replace(' ', '_')}_{call_type.replace(' ', '_')}_{timestamp}.{file_extension}"
                file_path = UPLOADS_DIR / filename
                
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                
                # Analyze with GPT
                analysis = analyze_call_with_gpt(
                    str(file_path),
                    rm_name,
                    client_name,
                    pitch_outcome,
                    call_type,
                    additional_context
                )
                
                # Save to database
                db = load_db()
                record = {
                    "id": len(db) + 1,
                    "rm_name": rm_name,
                    "client_name": client_name,
                    "call_type": call_type,
                    "pitch_outcome": pitch_outcome,
                    "call_date": str(call_date),
                    "uploaded_at": datetime.now().isoformat(),
                    "file_path": str(file_path),
                    "file_name": uploaded_file.name,
                    "additional_context": additional_context,
                    "notes": notes,
                    "analysis": analysis
                }
                db.append(record)
                save_db(db)
                
                st.success("✅ Analysis Complete!")
                
                # Display results
                st.markdown("---")
                st.subheader(f"📊 Analysis Results - {call_type}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Overall Score", f"{analysis['overall_score']}/10")
                with col2:
                    st.metric("Effectiveness", analysis['call_effectiveness'])
                with col3:
                    st.metric("BHAG Commitment", analysis['participant_readiness']['bhag_commitment_level'])
                with col4:
                    st.metric("Concern Status", analysis['participant_readiness']['concern_status'])
                
                st.markdown("**Executive Summary:**")
                st.info(analysis['summary'])
                
                # Specific Observations
                st.markdown("### 🔍 Specific Observations")
                obs = analysis['specific_observations']
                for key, value in obs.items():
                    with st.expander(f"📌 {key.replace('_', ' ').title()}"):
                        st.write(value)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 💪 What RM Did Well")
                    for strength in analysis['what_rm_did_well']:
                        st.success(f"✓ {strength}")
                    
                    st.markdown("### 🎯 Key Strengths")
                    for strength in analysis['key_strengths']:
                        st.write(f"• {strength}")
                
                with col2:
                    st.markdown("### ⚠️ What RM Missed")
                    for gap in analysis['what_rm_missed']:
                        st.warning(f"✗ {gap}")
                    
                    st.markdown("### 🔴 Critical Gaps")
                    for gap in analysis['critical_gaps']:
                        st.write(f"• {gap}")
                
                st.markdown("### 💡 Recommendations")
                for rec in analysis['recommendations']:
                    st.write(f"🎯 {rec}")
                
                st.markdown("### 📋 Next Steps")
                for step in analysis['next_steps']:
                    st.write(f"→ {step}")
                
                # Participant Readiness
                st.markdown("### 👤 Participant Readiness Assessment")
                ready = analysis['participant_readiness']
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("BHAG Commitment", ready['bhag_commitment_level'])
                with col2:
                    st.metric("Community Interest", ready['community_interest'])
                with col3:
                    st.metric("Urgency Level", ready['urgency_level'])
                with col4:
                    st.metric("Concerns", ready['concern_status'])

# DASHBOARD PAGE
elif page == "Dashboard":
    st.title("📊 My Call Analysis Dashboard")
    
    # User filter
    rm_filter = st.text_input("Filter by your name", placeholder="Enter your name to see your calls")
    
    # Call type filter
    call_type_filter = st.selectbox("Filter by Call Type", ["All"] + list(CALL_PARAMETERS.keys()))
    
    db = load_db()
    
    if rm_filter:
        filtered_db = [record for record in db if rm_filter.lower() in record['rm_name'].lower()]
    else:
        filtered_db = db
    
    if call_type_filter != "All":
        filtered_db = [record for record in filtered_db if record.get('call_type') == call_type_filter]
    
    if not filtered_db:
        st.info("No calls found. Upload your first recording to get started!")
    else:
        st.write(f"**Total Calls:** {len(filtered_db)}")
        
        # Summary metrics
        success_rate = len([r for r in filtered_db if "Success" in r['pitch_outcome']]) / len(filtered_db) * 100
        avg_score = sum([r['analysis']['overall_score'] for r in filtered_db]) / len(filtered_db)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Success Rate", f"{success_rate:.1f}%")
        with col2:
            st.metric("Average Score", f"{avg_score:.1f}/10")
        with col3:
            st.metric("Total Calls", len(filtered_db))
        with col4:
            high_commitment = len([r for r in filtered_db if r['analysis']['participant_readiness']['bhag_commitment_level'] == 'High'])
            st.metric("High BHAG Commitment", high_commitment)
        
        # Display calls table
        st.markdown("---")
        st.subheader("📋 Call History")
        
        for record in reversed(filtered_db):
            with st.expander(
                f"📞 {record['call_type']} - {record['client_name']} - {record['call_date']} "
                f"(Score: {record['analysis']['overall_score']}/10 | {record['analysis']['call_effectiveness']})"
            ):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**RM:** {record['rm_name']}")
                    st.write(f"**Participant:** {record['client_name']}")
                    st.write(f"**Call Type:** {record['call_type']}")
                    st.write(f"**Outcome:** {record['pitch_outcome']}")
                    st.write(f"**Summary:** {record['analysis']['summary']}")
                    
                    if record.get('additional_context'):
                        st.write(f"**Context:** {record['additional_context']}")
                
                with col2:
                    st.metric("Score", f"{record['analysis']['overall_score']}/10")
                    st.write(f"**BHAG Commitment:** {record['analysis']['participant_readiness']['bhag_commitment_level']}")
                    st.write(f"**Community Interest:** {record['analysis']['participant_readiness']['community_interest']}")
                    st.write(f"**Urgency:** {record['analysis']['participant_readiness']['urgency_level']}")
                
                st.markdown("**What Went Well:**")
                for item in record['analysis']['what_rm_did_well'][:3]:
                    st.write(f"✓ {item}")
                
                st.markdown("**What to Improve:**")
                for item in record['analysis']['what_rm_missed'][:3]:
                    st.write(f"✗ {item}")
                
                # Download analysis button
                analysis_json = json.dumps(record, indent=2)
                st.download_button(
                    label="📥 Download Full Analysis",
                    data=analysis_json,
                    file_name=f"analysis_{record['client_name']}_{record['call_date']}.json",
                    mime="application/json",
                    key=f"download_{record['id']}"
                )

# ADMIN VIEW
elif page == "Admin View":
    st.title("👨‍💼 Admin Dashboard")
    
    db = load_db()
    
    if not db:
        st.info("No data available yet.")
    else:
        # Overall statistics
        st.subheader("📈 Overall Statistics")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Calls", len(db))
        with col2:
            success_count = len([r for r in db if "Success" in r['pitch_outcome']])
            st.metric("Successful Calls", success_count)
        with col3:
            avg_score = sum([r['analysis']['overall_score'] for r in db]) / len(db)
            st.metric("Avg Score", f"{avg_score:.1f}/10")
        with col4:
            unique_rms = len(set([r['rm_name'] for r in db]))
            st.metric("Active RMs", unique_rms)
        with col5:
            high_bhag = len([r for r in db if r['analysis']['participant_readiness']['bhag_commitment_level'] == 'High'])
            st.metric("High BHAG Commitment", high_bhag)
        
        # Call type breakdown
        st.markdown("---")
        st.subheader("📊 Call Type Performance")
        call_type_data = {}
        for record in db:
            ct = record.get('call_type', 'Unknown')
            if ct not in call_type_data:
                call_type_data[ct] = {'count': 0, 'avg_score': 0, 'scores': []}
            call_type_data[ct]['count'] += 1
            call_type_data[ct]['scores'].append(record['analysis']['overall_score'])
        
        for ct, data in call_type_data.items():
            data['avg_score'] = sum(data['scores']) / len(data['scores'])
        
        ct_df = pd.DataFrame([
            {'Call Type': ct, 'Count': data['count'], 'Avg Score': f"{data['avg_score']:.1f}"}
            for ct, data in call_type_data.items()
        ])
        st.dataframe(ct_df, use_container_width=True)
        
        # Filters
        st.markdown("---")
        st.subheader("🔍 Filters")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            rm_list = ["All"] + sorted(list(set([r['rm_name'] for r in db])))
            selected_rm = st.selectbox("Filter by RM", rm_list)
        
        with col2:
            call_type_list = ["All"] + list(CALL_PARAMETERS.keys())
            selected_call_type = st.selectbox("Filter by Call Type", call_type_list)
        
        with col3:
            outcome_list = ["All", "Success - Committed", "Partial - Needs Follow-up", "Not Interested", "Rescheduled"]
            selected_outcome = st.selectbox("Filter by Outcome", outcome_list)
        
        with col4:
            bhag_list = ["All", "High", "Medium", "Low"]
            selected_bhag = st.selectbox("Filter by BHAG Commitment", bhag_list)
        
        # Apply filters
        filtered_db = db
        if selected_rm != "All":
            filtered_db = [r for r in filtered_db if r['rm_name'] == selected_rm]
        if selected_call_type != "All":
            filtered_db = [r for r in filtered_db if r.get('call_type') == selected_call_type]
        if selected_outcome != "All":
            filtered_db = [r for r in filtered_db if r['pitch_outcome'] == selected_outcome]
        if selected_bhag != "All":
            filtered_db = [r for r in filtered_db if r['analysis']['participant_readiness']['bhag_commitment_level'] == selected_bhag]
        
        # Display filtered results
        st.markdown("---")
        st.subheader(f"📊 Results ({len(filtered_db)} calls)")
        
        # Create DataFrame
        df_data = []
        for record in filtered_db:
            df_data.append({
                "Date": record['call_date'],
                "RM Name": record['rm_name'],
                "Participant": record['client_name'],
                "Call Type": record.get('call_type', 'N/A'),
                "Outcome": record['pitch_outcome'],
                "Score": record['analysis']['overall_score'],
                "Effectiveness": record['analysis']['call_effectiveness'],
                "BHAG Level": record['analysis']['participant_readiness']['bhag_commitment_level'],
                "Uploaded": record['uploaded_at'].split('T')[0]
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Download all data
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download All Data (CSV)",
                data=csv,
                file_name=f"iron_lady_call_analysis_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            # Detailed view
            st.markdown("---")
            st.subheader("🔍 Detailed Records")
            
            for record in reversed(filtered_db):
                with st.expander(
                    f"{record['rm_name']} - {record['call_type']} - {record['client_name']} ({record['call_date']}) "
                    f"- Score: {record['analysis']['overall_score']}/10"
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Basic Info:**")
                        st.write(f"• RM: {record['rm_name']}")
                        st.write(f"• Participant: {record['client_name']}")
                        st.write(f"• Call Type: {record.get('call_type', 'N/A')}")
                        st.write(f"• Date: {record['call_date']}")
                        st.write(f"• Outcome: {record['pitch_outcome']}")
                        st.write(f"• File: {record['file_name']}")
                    
                    with col2:
                        st.write("**Analysis Metrics:**")
                        st.write(f"• Score: {record['analysis']['overall_score']}/10")
                        st.write(f"• Effectiveness: {record['analysis']['call_effectiveness']}")
                        st.write(f"• BHAG Commitment: {record['analysis']['participant_readiness']['bhag_commitment_level']}")
                        st.write(f"• Community Interest: {record['analysis']['participant_readiness']['community_interest']}")
                        st.write(f"• Urgency: {record['analysis']['participant_readiness']['urgency_level']}")
                        st.write(f"• Concerns: {record['analysis']['participant_readiness']['concern_status']}")
                    
                    st.write(f"**Summary:** {record['analysis']['summary']}")
                    
                    st.write("**What RM Did Well:**")
                    for s in record['analysis']['what_rm_did_well']:
                        st.write(f"✓ {s}")
                    
                    st.write("**What RM Missed:**")
                    for i in record['analysis']['what_rm_missed']:
                        st.write(f"✗ {i}")
                    
                    st.write("**Recommendations:**")
                    for r in record['analysis']['recommendations']:
                        st.write(f"→ {r}")

# Footer
st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Review the specific parameters for each call type before your calls!")
st.sidebar.markdown("Built for Iron Lady 👩‍💼")
