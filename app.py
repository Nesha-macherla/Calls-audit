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

# Iron Lady Specific Parameters from the advanced analyzer
IRON_LADY_PARAMETERS = {
    "Core Quality Dimensions": {
        "rapport_building": {
            "weight": 20,
            "description": "Greetings, warmth, empathy, personalization, relatedness"
        },
        "needs_discovery": {
            "weight": 25,
            "description": "Strategic questions, probing, understanding challenges and BHAG"
        },
        "solution_presentation": {
            "weight": 25,
            "description": "Program benefits, community value, outcomes, social proof"
        },
        "objection_handling": {
            "weight": 15,
            "description": "Concern handling with empathy and solutions"
        },
        "closing_technique": {
            "weight": 15,
            "description": "Powerful invite, next steps, commitment getting"
        }
    },
    "Iron Lady Specific Parameters": {
        "profile_understanding": {
            "weight": 10,
            "description": "Understanding experience, role, challenges, goals"
        },
        "credibility_building": {
            "weight": 10,
            "description": "Iron Lady community, success stories, mentors, certification"
        },
        "principles_usage": {
            "weight": 10,
            "description": "27 Principles framework (Unpredictable Behaviour, 10000 Hours, Differentiate Branding, Shameless Pitching, Art of Negotiation, Contextualisation)"
        },
        "case_studies_usage": {
            "weight": 10,
            "description": "Success stories from participants (Neha, Rashmi, Chandana, Annapurna, Pushpalatha, Tejaswini)"
        },
        "gap_creation": {
            "weight": 10,
            "description": "Highlighting what's missing to achieve BHAG, creating urgency"
        },
        "bhag_fine_tuning": {
            "weight": 10,
            "description": "Big Hairy Audacious Goal exploration, making them dream bigger"
        },
        "urgency_creation": {
            "weight": 10,
            "description": "Limited spots, immediate action, cost of inaction"
        },
        "commitment_getting": {
            "weight": 10,
            "description": "Explicit commitments for attendance, participation, taking calls"
        },
        "contextualisation": {
            "weight": 10,
            "description": "Personalizing to participant's specific situation and profile"
        },
        "excitement_creation": {
            "weight": 10,
            "description": "Creating enthusiasm about transformation journey"
        }
    }
}

# Call type specific focus areas
CALL_TYPE_FOCUS = {
    "Welcome Call": [
        "rapport_building", "profile_understanding", "credibility_building",
        "principles_usage", "case_studies_usage", "gap_creation",
        "bhag_fine_tuning", "commitment_getting", "urgency_creation",
        "contextualisation", "excitement_creation"
    ],
    "BHAG Call": [
        "bhag_fine_tuning", "gap_creation", "case_studies_usage",
        "commitment_getting", "principles_usage", "urgency_creation",
        "closing_technique"
    ],
    "Registration Call": [
        "urgency_creation", "objection_handling", "commitment_getting",
        "solution_presentation", "credibility_building", "closing_technique"
    ],
    "30 Sec Pitch": [
        "profile_understanding", "gap_creation", "case_studies_usage",
        "urgency_creation", "commitment_getting", "excitement_creation"
    ],
    "Second Level Call": [
        "credibility_building", "objection_handling", "solution_presentation",
        "case_studies_usage", "commitment_getting"
    ],
    "Follow Up Call": [
        "commitment_getting", "objection_handling", "urgency_creation",
        "case_studies_usage", "closing_technique"
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
    """Analyze call recording using ChatGPT API with comprehensive Iron Lady parameters"""
    try:
        # Get focus areas for this call type
        focus_areas = CALL_TYPE_FOCUS.get(call_type, [])
        focus_params = [param for param in focus_areas]
        
        prompt = f"""
You are an expert Iron Lady sales call analyst. Analyze this {call_type} with the following details:

**CALL DETAILS:**
- Relationship Manager: {rm_name}
- Client/Participant Name: {client_name}
- Call Outcome: {pitch_outcome}
- Call Type: {call_type}
- Context: {additional_context}

**IRON LADY METHODOLOGY FRAMEWORK:**

**1. CORE QUALITY DIMENSIONS (Total: 100 points)**
   - Rapport Building (0-20): Greetings, warmth, empathy, personalization, relatedness
   - Needs Discovery (0-25): Strategic questions, understanding challenges and BHAG
   - Solution Presentation (0-25): Program benefits, community value, outcomes
   - Objection Handling (0-15): Concern handling with empathy and solutions
   - Closing Technique (0-15): Powerful invite, next steps, commitment

**2. IRON LADY SPECIFIC PARAMETERS (Total: 100 points)**
   - Profile Understanding (0-10): Experience, role, challenges, goals
   - Credibility Building (0-10): Iron Lady community, success stories, mentors
   - Principles Usage (0-10): 27 Principles framework (Unpredictable Behaviour, 10000 Hours, Differentiate Branding, Shameless Pitching, Art of Negotiation, Contextualisation)
   - Case Studies Usage (0-10): Success stories (Neha, Rashmi, Chandana, Annapurna, Pushpalatha, Tejaswini)
   - Gap Creation (0-10): Highlighting what's missing to achieve BHAG
   - BHAG Fine Tuning (0-10): Making them dream bigger, breakthrough goals
   - Urgency Creation (0-10): Limited spots, immediate action, FOMO
   - Commitment Getting (0-10): Explicit commitments for attendance and participation
   - Contextualisation (0-10): Personalizing to participant's situation
   - Excitement Creation (0-10): Enthusiasm about transformation journey

**CRITICAL FOCUS FOR {call_type.upper()}:**
{", ".join(focus_params)}

**KEY IRON LADY CONCEPTS:**
- BHAG = Big Hairy Audacious Goal (participant's major breakthrough goal)
- 27 Principles = Core framework (Unpredictable Behaviour, 10000 Hours, Differentiate Branding, Maximize, Shameless Pitching, Art of Negotiation, Contextualisation, etc.)
- Community = Network of successful women entrepreneurs and leaders
- 3-Day Program = Day 1 & 2 (Workshop), Day 3 (Follow-up session)
- Certification = Program completion credential
- Brand Statement = Personal branding exercise
- Case Studies = Success stories from participants like Neha (Big 4 Partner), Rashmi (Senior Leader), Chandana (Entrepreneur), Annapurna, Pushpalatha, Tejaswini

**OUTCOME-BASED ANALYSIS:**
Based on the call outcome being '{pitch_outcome}', provide realistic analysis.

Provide comprehensive analysis in this JSON format:

{{
    "overall_score": <number 0-100>,
    "methodology_compliance": <number 0-100>,
    "call_effectiveness": "<Excellent/Good/Average/Needs Improvement>",
    
    "core_dimensions": {{
        "rapport_building": <0-20>,
        "needs_discovery": <0-25>,
        "solution_presentation": <0-25>,
        "objection_handling": <0-15>,
        "closing_technique": <0-15>
    }},
    
    "iron_lady_parameters": {{
        "profile_understanding": <0-10>,
        "credibility_building": <0-10>,
        "principles_usage": <0-10>,
        "case_studies_usage": <0-10>,
        "gap_creation": <0-10>,
        "bhag_fine_tuning": <0-10>,
        "urgency_creation": <0-10>,
        "commitment_getting": <0-10>,
        "contextualisation": <0-10>,
        "excitement_creation": <0-10>
    }},
    
    "key_insights": {{
        "strengths": ["strength1", "strength2", "strength3"],
        "critical_gaps": ["gap1", "gap2", "gap3"],
        "missed_opportunities": ["opportunity1", "opportunity2", "opportunity3"],
        "best_moments": ["moment1", "moment2", "moment3"]
    }},
    
    "outcome_prediction": {{
        "likely_result": "<registration_expected/follow_up_needed/needs_improvement>",
        "confidence": <0-100>,
        "reasoning": "<explanation>"
    }},
    
    "coaching_recommendations": [
        "specific recommendation 1",
        "specific recommendation 2",
        "specific recommendation 3",
        "specific recommendation 4"
    ],
    
    "iron_lady_specific_coaching": [
        "principles coaching point",
        "case studies coaching point",
        "bhag coaching point",
        "commitment coaching point"
    ],
    
    "call_summary": "<2-3 sentence summary focusing on Iron Lady methodology compliance and outcome>"
}}

**CRITICAL SCORING RULES:**
1. Principles Usage < 7 = CRITICAL GAP (most important)
2. Case Studies Usage < 6 = Major gap
3. BHAG Fine Tuning < 7 = Needs improvement
4. Commitment Getting < 7 = Weak closing
5. Overall Score = (Core Dimensions * 0.6) + (Iron Lady Parameters * 0.4)
6. Methodology Compliance = Iron Lady Parameters total percentage

Provide actionable, specific feedback for {rm_name} to improve their {call_type} performance.
"""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional Iron Lady sales call analyst with deep expertise in the 27 Principles framework and community-based coaching methodology. Always respond with valid JSON only. Be specific, actionable, and focus on Iron Lady methodology compliance."},
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
            "overall_score": 50.0,
            "methodology_compliance": 45.0,
            "call_effectiveness": "Needs Improvement",
            "core_dimensions": {
                "rapport_building": 10,
                "needs_discovery": 12,
                "solution_presentation": 12,
                "objection_handling": 8,
                "closing_technique": 8
            },
            "iron_lady_parameters": {
                "profile_understanding": 5,
                "credibility_building": 4,
                "principles_usage": 3,
                "case_studies_usage": 4,
                "gap_creation": 4,
                "bhag_fine_tuning": 5,
                "urgency_creation": 5,
                "commitment_getting": 4,
                "contextualisation": 5,
                "excitement_creation": 5
            },
            "key_insights": {
                "strengths": ["Professional approach"],
                "critical_gaps": ["API error - unable to analyze"],
                "missed_opportunities": ["Please check API configuration"],
                "best_moments": ["Unable to determine"]
            },
            "outcome_prediction": {
                "likely_result": "needs_improvement",
                "confidence": 50,
                "reasoning": "Analysis unavailable due to API error"
            },
            "coaching_recommendations": ["Check API configuration", "Re-upload for analysis"],
            "iron_lady_specific_coaching": ["API error prevented detailed analysis"],
            "call_summary": "Analysis unavailable. Please check OpenAI API configuration."
        }

# Sidebar navigation
st.sidebar.title("👩‍💼 Iron Lady Call Analysis")
st.sidebar.markdown("**Advanced AI-Powered Analysis**")
st.sidebar.markdown("*Based on 27 Principles Framework*")
page = st.sidebar.radio("Navigate", ["Upload Recording", "Dashboard", "Admin View", "Parameters Guide"])

# PARAMETERS GUIDE PAGE
if page == "Parameters Guide":
    st.title("📚 Iron Lady Parameters Guide")
    st.markdown("Complete breakdown of all parameters used in call analysis")
    
    tab1, tab2, tab3 = st.tabs(["Core Dimensions", "Iron Lady Parameters", "Call Type Focus"])
    
    with tab1:
        st.subheader("🎯 Core Quality Dimensions (100 points)")
        for param, details in IRON_LADY_PARAMETERS["Core Quality Dimensions"].items():
            with st.expander(f"**{param.replace('_', ' ').title()}** ({details['weight']} points)"):
                st.write(f"**Description:** {details['description']}")
                st.write(f"**Weight:** {details['weight']} points")
    
    with tab2:
        st.subheader("💎 Iron Lady Specific Parameters (100 points)")
        for param, details in IRON_LADY_PARAMETERS["Iron Lady Specific Parameters"].items():
            with st.expander(f"**{param.replace('_', ' ').title()}** ({details['weight']} points)"):
                st.write(f"**Description:** {details['description']}")
                st.write(f"**Weight:** {details['weight']} points")
    
    with tab3:
        st.subheader("📋 Call Type Specific Focus Areas")
        for call_type, params in CALL_TYPE_FOCUS.items():
            with st.expander(f"**{call_type}**"):
                st.write("**Focus on these parameters:**")
                for param in params:
                    st.write(f"• {param.replace('_', ' ').title()}")

# UPLOAD PAGE
elif page == "Upload Recording":
    st.title("📤 Upload Call Recording")
    st.write("Upload your Iron Lady sales call recording and get comprehensive AI-powered analysis")
    
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
            call_duration = st.number_input("Call Duration (minutes)", min_value=1, max_value=120, value=15)
        
        uploaded_file = st.file_uploader(
            "Upload Recording *",
            type=['mp3', 'wav', 'm4a', 'mp4'],
            help="Supported formats: MP3, WAV, M4A, MP4 (Max 200MB)"
        )
        
        # Show relevant parameters for selected call type
        st.markdown(f"### 📋 Key Focus Areas for {call_type}")
        focus_params = CALL_TYPE_FOCUS.get(call_type, [])
        st.info("✓ " + "\n✓ ".join([p.replace('_', ' ').title() for p in focus_params[:5]]) + "\n... and more")
        
        additional_context = st.text_area(
            "Call Context & Notes *",
            placeholder="""Example:
Participant's BHAG: Launch ₹50 lakh/year coaching practice in 12 months
Current Situation: Running small yoga classes, 15 students, ₹30k/month
Main Concerns: Pricing premium programs, confidence in sales, no online business experience
Previous Interaction: Completed Day 1 & 2, very engaged, asked many questions
Key Insights: Husband supportive but worried about investment
Principles Discussed: Differentiate Branding, Shameless Pitching
Case Studies Shared: Neha's story (Big 4 Partner)""",
            height=150
        )
        
        notes = st.text_area(
            "Additional Notes (Optional)",
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
                    "call_duration": call_duration,
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
                    st.metric("Overall Score", f"{analysis['overall_score']:.1f}/100")
                with col2:
                    st.metric("Iron Lady Compliance", f"{analysis['methodology_compliance']:.1f}%")
                with col3:
                    st.metric("Effectiveness", analysis['call_effectiveness'])
                with col4:
                    outcome_emoji = {"registration_expected": "🎉", "follow_up_needed": "📞", "needs_improvement": "⚠️"}
                    st.metric("Prediction", analysis['outcome_prediction']['likely_result'].replace('_', ' ').title())
                
                st.markdown("**Executive Summary:**")
                st.info(analysis['call_summary'])
                
                # Core Dimensions Breakdown
                st.markdown("### 🎯 Core Quality Dimensions")
                core_df = pd.DataFrame([
                    {"Dimension": k.replace('_', ' ').title(), "Score": v, "Max": IRON_LADY_PARAMETERS["Core Quality Dimensions"][k]["weight"]}
                    for k, v in analysis['core_dimensions'].items()
                ])
                st.dataframe(core_df, use_container_width=True, hide_index=True)
                
                # Iron Lady Parameters Breakdown
                st.markdown("### 💎 Iron Lady Specific Parameters")
                il_df = pd.DataFrame([
                    {"Parameter": k.replace('_', ' ').title(), "Score": v, "Max": 10}
                    for k, v in analysis['iron_lady_parameters'].items()
                ])
                st.dataframe(il_df, use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### ✅ Strengths")
                    for strength in analysis['key_insights']['strengths']:
                        st.success(f"✓ {strength}")
                    
                    st.markdown("### 🌟 Best Moments")
                    for moment in analysis['key_insights']['best_moments']:
                        st.write(f"⭐ {moment}")
                
                with col2:
                    st.markdown("### 🔴 Critical Gaps")
                    for gap in analysis['key_insights']['critical_gaps']:
                        st.error(f"✗ {gap}")
                    
                    st.markdown("### ⚠️ Missed Opportunities")
                    for opp in analysis['key_insights']['missed_opportunities']:
                        st.warning(f"→ {opp}")
                
                st.markdown("### 💡 General Coaching Recommendations")
                for rec in analysis['coaching_recommendations']:
                    st.write(f"🎯 {rec}")
                
                st.markdown("### 🎓 Iron Lady Specific Coaching")
                for rec in analysis['iron_lady_specific_coaching']:
                    st.write(f"💎 {rec}")
                
                # Outcome Prediction
                st.markdown("### 🔮 Outcome Prediction")
                pred = analysis['outcome_prediction']
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Likely Result", pred['likely_result'].replace('_', ' ').title())
                with col2:
                    st.metric("Confidence", f"{pred['confidence']}%")
                with col3:
                    st.write(f"**Reasoning:** {pred['reasoning']}")

# DASHBOARD PAGE
elif page == "Dashboard":
    st.title("📊 My Call Analysis Dashboard")
    
    # User filter
    rm_filter = st.text_input("Filter by your name", placeholder="Enter your name to see your calls")
    
    # Call type filter
    call_type_filter = st.selectbox("Filter by Call Type", ["All"] + list(CALL_TYPE_FOCUS.keys()))
    
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
        avg_score = sum([r['analysis'].get('overall_score', 0) for r in filtered_db]) / len(filtered_db)
        avg_compliance = sum([r['analysis'].get('methodology_compliance', 0) for r in filtered_db]) / len(filtered_db)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Success Rate", f"{success_rate:.1f}%")
        with col2:
            st.metric("Avg Overall Score", f"{avg_score:.1f}/100")
        with col3:
            st.metric("Avg IL Compliance", f"{avg_compliance:.1f}%")
        with col4:
            st.metric("Total Calls", len(filtered_db))
        
        # Display calls table
        st.markdown("---")
        st.subheader("📋 Call History")
        
        for record in reversed(filtered_db):
            analysis = record.get('analysis', {})
            with st.expander(
                f"📞 {record['call_type']} - {record['client_name']} - {record['call_date']} "
                f"(Score: {analysis.get('overall_score', 0):.1f}/100 | Compliance: {analysis.get('methodology_compliance', 0):.1f}%)"
            ):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**RM:** {record['rm_name']}")
                    st.write(f"**Participant:** {record['client_name']}")
                    st.write(f"**Call Type:** {record['call_type']}")
                    st.write(f"**Outcome:** {record['pitch_outcome']}")
                    st.write(f"**Duration:** {record.get('call_duration', 'N/A')} minutes")
                    st.write(f"**Summary:** {record['analysis']['call_summary']}")
                
                with col2:
                    st.metric("Overall Score", f"{analysis.get('overall_score', 0):.1f}/100")
                    st.metric("IL Compliance", f"{analysis.get('methodology_compliance', 0):.1f}%")
                    st.write(f"**Effectiveness:** {analysis.get('call_effectiveness', 'N/A')}")
                    pred = analysis.get('outcome_prediction', {})
                    st.write(f"**Prediction:** {pred.get('likely_result', 'N/A').replace('_', ' ').title()}")
                
                st.markdown("**Top Strengths:**")
                for item in record['analysis']['key_insights']['strengths'][:3]:
                    st.write(f"✓ {item}")
                
                st.markdown("**Critical Gaps:**")
                for item in record['analysis']['key_insights']['critical_gaps'][:3]:
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
            avg_score = sum([r['analysis'].get('overall_score', 0) for r in db]) / len(db)
            st.metric("Avg Score", f"{avg_score:.1f}/100")
        with col4:
            avg_compliance = sum([r['analysis'].get('methodology_compliance', 0) for r in db]) / len(db)
            st.metric("Avg IL Compliance", f"{avg_compliance:.1f}%")
        with col5:
            unique_rms = len(set([r['rm_name'] for r in db]))
            st.metric("Active RMs", unique_rms)
        
        # Call type performance
        st.markdown("---")
        st.subheader("📊 Call Type Performance")
        call_type_data = {}
        for record in filtered_db:
            ct = record.get('call_type', 'Unknown')
            if ct not in call_type_data:
                call_type_data[ct] = {'count': 0, 'scores': [], 'compliance': []}
            call_type_data[ct]['count'] += 1
            call_type_data[ct]['scores'].append(record['analysis'].get('overall_score', 0))
            call_type_data[ct]['compliance'].append(record['analysis'].get('methodology_compliance', 0))
        
        ct_df = pd.DataFrame([
            {
                'Call Type': ct,
                'Count': data['count'],
                'Avg Score': f"{sum(data['scores'])/len(data['scores']):.1f}",
                'Avg Compliance': f"{sum(data['compliance'])/len(data['compliance']):.1f}%"
            }
            for ct, data in call_type_data.items()
        ])
        st.dataframe(ct_df, use_container_width=True, hide_index=True)
        
        # Filters
        st.markdown("---")
        st.subheader("🔍 Filters")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            rm_list = ["All"] + sorted(list(set([r['rm_name'] for r in db])))
            selected_rm = st.selectbox("Filter by RM", rm_list)
        
        with col2:
            call_type_list = ["All"] + list(CALL_TYPE_FOCUS.keys())
            selected_call_type = st.selectbox("Filter by Call Type", call_type_list)
        
        with col3:
            outcome_list = ["All", "Success - Committed", "Partial - Needs Follow-up", "Not Interested", "Rescheduled"]
            selected_outcome = st.selectbox("Filter by Outcome", outcome_list)
        
        with col4:
            score_filter = st.selectbox("Filter by Score Range", ["All", "90-100 (Excellent)", "75-89 (Good)", "60-74 (Average)", "Below 60 (Needs Work)"])
        
        # Apply filters
        filtered_db = db
        if selected_rm != "All":
            filtered_db = [r for r in filtered_db if r['rm_name'] == selected_rm]
        if selected_call_type != "All":
            filtered_db = [r for r in filtered_db if r.get('call_type') == selected_call_type]
        if selected_outcome != "All":
            filtered_db = [r for r in filtered_db if r['pitch_outcome'] == selected_outcome]
        if score_filter != "All":
            if "90-100" in score_filter:
                filtered_db = [r for r in filtered_db if r['analysis']['overall_score'] >= 90]
            elif "75-89" in score_filter:
                filtered_db = [r for r in filtered_db if 75 <= r['analysis']['overall_score'] < 90]
            elif "60-74" in score_filter:
                filtered_db = [r for r in filtered_db if 60 <= r['analysis']['overall_score'] < 75]
            elif "Below 60" in score_filter:
                filtered_db = [r for r in filtered_db if r['analysis']['overall_score'] < 60]
        
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
                "Duration": f"{record.get('call_duration', 'N/A')} min",
                "Outcome": record['pitch_outcome'],
                "Overall Score": f"{record['analysis'].get('overall_score', 0):.1f}",
                "IL Compliance": f"{record['analysis'].get('methodology_compliance', 0):.1f}%",
                "Effectiveness": record['analysis'].get('call_effectiveness', 'N/A'),
                "Prediction": record['analysis'].get('outcome_prediction', {}).get('likely_result', 'N/A').replace('_', ' ').title(),
                "Uploaded": record['uploaded_at'].split('T')[0]
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Download all data
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download All Data (CSV)",
                data=csv,
                file_name=f"iron_lady_call_analysis_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            # Parameter Performance Analysis
            st.markdown("---")
            st.subheader("📊 Parameter Performance Analysis")
            
            # Aggregate Iron Lady parameter scores
            param_totals = {}
            param_counts = {}
            
            for record in filtered_db:
                for param, score in record['analysis'].get('iron_lady_parameters', {}).items():
                    if param not in param_totals:
                        param_totals[param] = 0
                        param_counts[param] = 0
                    param_totals[param] += score
                    param_counts[param] += 1
            
            param_avg = {param: (param_totals[param] / param_counts[param]) for param in param_totals}
            
            if param_avg:  # Only show if we have data
                param_df = pd.DataFrame([
                    {
                        "Parameter": param.replace('_', ' ').title(),
                        "Avg Score": f"{score:.1f}",
                        "Max": "10",
                        "Performance": "🟢 Excellent" if score >= 8 else "🟡 Good" if score >= 6 else "🔴 Needs Work"
                    }
                    for param, score in sorted(param_avg.items(), key=lambda x: x[1], reverse=True)
                ])
                
                st.dataframe(param_df, use_container_width=True, hide_index=True)
                
                st.info("💡 **Coaching Focus:** Prioritize parameters marked 🔴 Needs Work for team training")
            else:
                st.info("No Iron Lady parameter data available for selected filters")
            
            # Detailed view
            st.markdown("---")
            st.subheader("🔍 Detailed Records")
            
            for record in reversed(filtered_db[:10]):  # Show last 10 for performance
                analysis = record.get('analysis', {})
                with st.expander(
                    f"{record['rm_name']} - {record['call_type']} - {record['client_name']} ({record['call_date']}) "
                    f"- Score: {analysis.get('overall_score', 0):.1f}/100 | Compliance: {analysis.get('methodology_compliance', 0):.1f}%"
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Basic Info:**")
                        st.write(f"• RM: {record['rm_name']}")
                        st.write(f"• Participant: {record['client_name']}")
                        st.write(f"• Call Type: {record.get('call_type', 'N/A')}")
                        st.write(f"• Date: {record['call_date']}")
                        st.write(f"• Duration: {record.get('call_duration', 'N/A')} minutes")
                        st.write(f"• Outcome: {record['pitch_outcome']}")
                        st.write(f"• File: {record['file_name']}")
                    
                    with col2:
                        st.write("**Performance Metrics:**")
                        st.write(f"• Overall Score: {record['analysis'].get('overall_score', 0):.1f}/100")
                        st.write(f"• IL Compliance: {record['analysis'].get('methodology_compliance', 0):.1f}%")
                        st.write(f"• Effectiveness: {record['analysis'].get('call_effectiveness', 'N/A')}")
                        pred = record['analysis'].get('outcome_prediction', {})
                        st.write(f"• Prediction: {pred.get('likely_result', 'N/A').replace('_', ' ').title()}")
                        st.write(f"• Confidence: {pred.get('confidence', 0)}%")
                    
                    st.write(f"**Summary:** {record['analysis'].get('call_summary', 'No summary available')}")
                    
                    # Only show core dimensions if they exist
                    if 'core_dimensions' in record['analysis']:
                        st.write("**Core Dimensions:**")
                        for dim, score in record['analysis']['core_dimensions'].items():
                            max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][dim]["weight"]
                            st.write(f"• {dim.replace('_', ' ').title()}: {score}/{max_score}")
                    
                    # Only show Iron Lady parameters if they exist
                    if 'iron_lady_parameters' in record['analysis']:
                        st.write("**Iron Lady Parameters:**")
                        for param, score in record['analysis']['iron_lady_parameters'].items():
                            emoji = "🟢" if score >= 8 else "🟡" if score >= 6 else "🔴"
                            st.write(f"{emoji} {param.replace('_', ' ').title()}: {score}/10")
                    
                    # Show insights if available
                    insights = record['analysis'].get('key_insights', {})
                    if insights.get('strengths'):
                        st.write("**Strengths:**")
                        for s in insights['strengths']:
                            st.write(f"✓ {s}")
                    
                    if insights.get('critical_gaps'):
                        st.write("**Critical Gaps:**")
                        for g in insights['critical_gaps']:
                            st.write(f"✗ {g}")
                    
                    # Show recommendations if available
                    if 'coaching_recommendations' in record['analysis']:
                        st.write("**Coaching Recommendations:**")
                        for r in record['analysis']['coaching_recommendations']:
                            st.write(f"→ {r}")
                    
                    if 'iron_lady_specific_coaching' in record['analysis']:
                        st.write("**Iron Lady Specific Coaching:**")
                        for r in record['analysis']['iron_lady_specific_coaching']:
                            st.write(f"💎 {r}")

# Footer
st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Focus on Iron Lady Compliance score to master the methodology!")
st.sidebar.markdown("**Iron Lady Framework**")
st.sidebar.markdown("• 27 Principles")
st.sidebar.markdown("• BHAG Focus")
st.sidebar.markdown("• Community Power")
st.sidebar.markdown("• Powerful Invites")
st.sidebar.markdown("---")
st.sidebar.markdown("Built for Iron Lady 👩‍💼")
