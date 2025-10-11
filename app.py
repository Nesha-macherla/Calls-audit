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

# Iron Lady Specific Parameters
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

def delete_record(record_id):
    """Delete a record from the database"""
    db = load_db()
    db = [r for r in db if r['id'] != record_id]
    save_db(db)
    return True

def analyze_call_with_gpt(call_type, additional_context, manual_scores=None):
    """
    Hybrid analysis: Uses GPT for insights but allows manual score override
    If manual_scores provided, uses those; otherwise GPT analyzes
    """
    try:
        # If manual scores provided, use them directly
        if manual_scores:
            return generate_analysis_from_scores(manual_scores, call_type, "Manual scoring with GPT-generated insights")
        
        # Otherwise, use GPT to analyze
        focus_areas = CALL_TYPE_FOCUS.get(call_type, [])
        focus_params = [param for param in focus_areas]
        
        prompt = f"""You are an expert Iron Lady sales call analyst. Analyze this {call_type} and provide scores.

**CALL CONTEXT:**
{additional_context}

**CRITICAL: You must provide REALISTIC scores based on the actual content described. Do NOT give default 50% scores.**

**SCORING INSTRUCTIONS:**

**CORE DIMENSIONS:**
1. Rapport Building (0-20): Did they use names, show warmth, build connection?
2. Needs Discovery (0-25): How many strategic questions? Did they explore BHAG deeply?
3. Solution Presentation (0-25): Did they explain program benefits, community, outcomes?
4. Objection Handling (0-15): How well did they address concerns?
5. Closing Technique (0-15): Did they use "powerfully invite" and get commitments?

**IRON LADY PARAMETERS (each 0-10):**
1. Profile Understanding: Did they understand background, role, goals?
2. Credibility Building: Did they mention Iron Lady community, success stories?
3. Principles Usage: Did they mention ANY of the 27 Principles by name?
4. Case Studies Usage: Did they mention specific participant names (Neha, Rashmi, etc.)?
5. Gap Creation: Did they highlight what's missing to achieve BHAG?
6. BHAG Fine Tuning: Did they explore and expand the BHAG?
7. Urgency Creation: Did they create FOMO, mention limited spots?
8. Commitment Getting: Did they get explicit commitments?
9. Contextualisation: Did they personalize to the participant's situation?
10. Excitement Creation: Did they generate enthusiasm?

**SCORING RULES:**
- If something was NOT done or mentioned → Score 0-3
- If barely mentioned → Score 4-6
- If done well → Score 7-8
- If done excellently with specifics → Score 9-10

**CRITICAL RULES:**
- NO principles mentioned by name = MAX 3 points for Principles Usage
- NO specific case study names = MAX 4 points for Case Studies Usage
- NO BHAG exploration = MAX 4 points for BHAG Fine Tuning
- NO explicit commitments = MAX 4 points for Commitment Getting

Respond ONLY with this JSON format (no other text):

{{
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
    "justification": "Brief explanation of scores based on what was actually done in the call"
}}
"""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert call analyst. Provide realistic scores based on actual performance described. Never give default 50% scores. Be strict but fair."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        analysis_text = response.choices[0].message.content
        scores_data = json.loads(analysis_text)
        
        # Generate full analysis from GPT scores
        return generate_analysis_from_scores(
            scores_data.get('core_dimensions', {}),
            call_type,
            scores_data.get('justification', 'GPT analysis'),
            scores_data.get('iron_lady_parameters', {})
        )
        
    except Exception as e:
        st.error(f"GPT Analysis Error: {str(e)}")
        # Return neutral scores on error
        return generate_analysis_from_scores({
            "rapport_building": 10,
            "needs_discovery": 12,
            "solution_presentation": 12,
            "objection_handling": 8,
            "closing_technique": 8
        }, call_type, f"Error in analysis: {str(e)}")

def generate_analysis_from_scores(core_dims, call_type, justification, il_params=None):
    """Generate complete analysis from scores"""
    
    # Ensure all core dimensions are present
    core_dimensions = {
        "rapport_building": core_dims.get("rapport_building", 10),
        "needs_discovery": core_dims.get("needs_discovery", 12),
        "solution_presentation": core_dims.get("solution_presentation", 12),
        "objection_handling": core_dims.get("objection_handling", 8),
        "closing_technique": core_dims.get("closing_technique", 8)
    }
    
    # Ensure all IL parameters are present
    if il_params is None:
        il_params = {}
    
    iron_lady_parameters = {
        "profile_understanding": il_params.get("profile_understanding", 5),
        "credibility_building": il_params.get("credibility_building", 5),
        "principles_usage": il_params.get("principles_usage", 5),
        "case_studies_usage": il_params.get("case_studies_usage", 5),
        "gap_creation": il_params.get("gap_creation", 5),
        "bhag_fine_tuning": il_params.get("bhag_fine_tuning", 5),
        "urgency_creation": il_params.get("urgency_creation", 5),
        "commitment_getting": il_params.get("commitment_getting", 5),
        "contextualisation": il_params.get("contextualisation", 5),
        "excitement_creation": il_params.get("excitement_creation", 5)
    }
    
    # Calculate scores
    core_total = sum(core_dimensions.values())
    il_total = sum(iron_lady_parameters.values())
    
    overall_score = (core_total * 0.6) + (il_total * 0.4)
    methodology_compliance = il_total
    
    # Determine effectiveness
    if overall_score >= 85:
        effectiveness = "Excellent"
    elif overall_score >= 70:
        effectiveness = "Good"
    elif overall_score >= 50:
        effectiveness = "Average"
    else:
        effectiveness = "Needs Improvement"
    
    # Generate insights
    strengths = []
    critical_gaps = []
    missed_opportunities = []
    best_moments = []
    
    # Analyze core dimensions
    for param, score in core_dimensions.items():
        max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][param]["weight"]
        percentage = (score / max_score) * 100
        param_name = param.replace('_', ' ').title()
        
        if percentage >= 80:
            strengths.append(f"Strong {param_name} - {score}/{max_score} ({percentage:.0f}%)")
            best_moments.append(f"Excellent execution of {param_name}")
        elif percentage < 50:
            critical_gaps.append(f"Weak {param_name} - only {score}/{max_score} ({percentage:.0f}%)")
            missed_opportunities.append(f"Significant improvement needed in {param_name}")
    
    # Analyze IL parameters
    for param, score in iron_lady_parameters.items():
        percentage = (score / 10) * 100
        param_name = param.replace('_', ' ').title()
        
        if percentage >= 80:
            strengths.append(f"Strong {param_name} - {score}/10")
        elif percentage < 50:
            critical_gaps.append(f"Weak {param_name} - only {score}/10")
            missed_opportunities.append(f"Must improve {param_name}")
    
    # Ensure minimum insights
    if not strengths:
        strengths = ["Professional demeanor maintained", "Basic structure followed"]
    if not critical_gaps:
        critical_gaps = ["Fine-tune delivery", "Enhance engagement"]
    if not missed_opportunities:
        missed_opportunities = ["Deepen rapport", "Strengthen methodology"]
    if not best_moments:
        best_moments = ["Call completed professionally"]
    
    # Generate coaching
    coaching_recommendations = []
    il_coaching = []
    
    sorted_core = sorted(core_dimensions.items(), key=lambda x: x[1])
    sorted_il = sorted(iron_lady_parameters.items(), key=lambda x: x[1])
    
    for param, score in sorted_core[:3]:
        max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][param]["weight"]
        if score < max_score * 0.7:
            coaching_recommendations.append(
                f"Priority: Improve {param.replace('_', ' ').title()} from {score}/{max_score} to at least {int(max_score*0.8)}/{max_score}"
            )
    
    for param, score in sorted_il[:4]:
        if score < 7:
            il_coaching.append(
                f"Focus: {param.replace('_', ' ').title()} needs work (current: {score}/10, target: 8+/10)"
            )
    
    if not coaching_recommendations:
        coaching_recommendations = ["Maintain current performance levels", "Continue professional approach"]
    
    if not il_coaching:
        il_coaching = ["Integrate more 27 Principles", "Use specific case studies", "Deepen BHAG exploration"]
    
    # Outcome prediction
    commit_score = iron_lady_parameters.get('commitment_getting', 0)
    bhag_score = iron_lady_parameters.get('bhag_fine_tuning', 0)
    
    if overall_score >= 80 and commit_score >= 7 and bhag_score >= 7:
        likely_result = "registration_expected"
        confidence = min(95, int(overall_score + 5))
        reasoning = f"Strong performance (score: {overall_score:.0f}/100) with solid commitments and BHAG work"
    elif overall_score >= 60:
        likely_result = "follow_up_needed"
        confidence = min(80, int(overall_score - 5))
        reasoning = f"Moderate performance (score: {overall_score:.0f}/100), follow-up required to secure commitment"
    else:
        likely_result = "needs_improvement"
        confidence = min(70, int(overall_score - 15))
        reasoning = f"Below standard performance (score: {overall_score:.0f}/100), significant improvement needed"
    
    # Generate summary
    summary = f"{call_type} scored {overall_score:.1f}/100 with {methodology_compliance:.1f}% Iron Lady compliance. {justification}"
    
    return {
        "overall_score": round(overall_score, 1),
        "methodology_compliance": round(methodology_compliance, 1),
        "call_effectiveness": effectiveness,
        "core_dimensions": core_dimensions,
        "iron_lady_parameters": iron_lady_parameters,
        "key_insights": {
            "strengths": strengths[:5],
            "critical_gaps": critical_gaps[:5],
            "missed_opportunities": missed_opportunities[:5],
            "best_moments": best_moments[:5]
        },
        "outcome_prediction": {
            "likely_result": likely_result,
            "confidence": confidence,
            "reasoning": reasoning
        },
        "coaching_recommendations": coaching_recommendations[:6],
        "iron_lady_specific_coaching": il_coaching[:6],
        "call_summary": summary
    }

# Sidebar navigation
st.sidebar.title("👩‍💼 Iron Lady Call Analysis")
st.sidebar.markdown("**Hybrid GPT + Manual Analysis**")
st.sidebar.markdown("*Based on 27 Principles Framework*")
page = st.sidebar.radio("Navigate", ["Upload & Analyze", "Dashboard", "Admin View", "Parameters Guide"])

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
elif page == "Upload & Analyze":
    st.title("📤 Upload Call & Get AI Analysis")
    st.write("Choose: Let GPT analyze OR manually score parameters")
    
    # Analysis mode selector
    analysis_mode = st.radio(
        "Analysis Mode:",
        ["🤖 GPT Auto-Analysis (Recommended)", "✍️ Manual Scoring"],
        horizontal=True
    )
    
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
            help="Supported formats: MP3, WAV, M4A, MP4 (Max 40MB)"
        )
        
        st.markdown(f"### 📋 Key Focus for {call_type}")
        focus_params = CALL_TYPE_FOCUS.get(call_type, [])
        st.info("✓ " + " • ".join([p.replace('_', ' ').title() for p in focus_params[:5]]))
        
        # Context field for GPT mode
        if "GPT" in analysis_mode:
            additional_context = st.text_area(
                "Call Summary & Key Details * (For GPT Analysis)",
                placeholder="""Describe what happened in the call:
- What questions were asked?
- Which principles were mentioned (by name)?
- Which case studies were shared (with names)?
- Was BHAG explored? How deeply?
- What commitments were obtained?
- How were objections handled?
- Was "powerfully invite" language used?

Example:
"RM asked 8 questions about participant's business. Discussed 'Differentiate Branding' and 'Shameless Pitching' principles. Shared Neha's case study (Big 4 Partner). Explored BHAG deeply - participant wants ₹50L/year practice. Got commitment to attend Day 2 & 3. Used 'powerfully invite' in closing. Created urgency about limited cohort spots."
""",
                height=200
            )
        else:
            additional_context = ""
            st.info("💡 Manual mode: Score each parameter below based on call performance")
            
            st.markdown("### 🎯 Core Quality Dimensions")
            col1, col2 = st.columns(2)
            
            with col1:
                rapport_building = st.slider("Rapport Building", 0, 20, 10, help="0-20 points")
                needs_discovery = st.slider("Needs Discovery", 0, 25, 12, help="0-25 points")
                solution_presentation = st.slider("Solution Presentation", 0, 25, 12, help="0-25 points")
            
            with col2:
                objection_handling = st.slider("Objection Handling", 0, 15, 8, help="0-15 points")
                closing_technique = st.slider("Closing Technique", 0, 15, 8, help="0-15 points")
            
            st.markdown("### 💎 Iron Lady Parameters")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                profile_understanding = st.slider("Profile Understanding", 0, 10, 5)
                credibility_building = st.slider("Credibility Building", 0, 10, 5)
                principles_usage = st.slider("27 Principles Usage", 0, 10, 5)
            
            with col2:
                case_studies_usage = st.slider("Case Studies Usage", 0, 10, 5)
                gap_creation = st.slider("Gap Creation", 0, 10, 5)
                bhag_fine_tuning = st.slider("BHAG Fine Tuning", 0, 10, 5)
            
            with col3:
                urgency_creation = st.slider("Urgency Creation", 0, 10, 5)
                commitment_getting = st.slider("Commitment Getting", 0, 10, 5)
                contextualisation = st.slider("Contextualisation", 0, 10, 5)
            
            excitement_creation = st.slider("Excitement Creation", 0, 10, 5)
        
        notes = st.text_area("Additional Notes (Optional)", placeholder="Any observations...")
        
        submitted = st.form_submit_button("🚀 Analyze Call", use_container_width=True)
    
    if submitted:
        if not all([rm_name, client_name, uploaded_file]):
            st.error("❌ Please fill all required fields (*)")
        elif "GPT" in analysis_mode and (not additional_context or len(additional_context.strip()) < 100):
            st.error("❌ Please provide detailed call summary (minimum 100 characters) for GPT analysis")
        else:
            with st.spinner(f"🔄 Analyzing {call_type}..."):
                # Save file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_extension = uploaded_file.name.split('.')[-1]
                filename = f"{rm_name.replace(' ', '_')}_{call_type.replace(' ', '_')}_{timestamp}.{file_extension}"
                file_path = UPLOADS_DIR / filename
                
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                
                # Analyze based on mode
                if "GPT" in analysis_mode:
                    analysis = analyze_call_with_gpt(call_type, additional_context)
                else:
                    manual_scores = {
                        "rapport_building": rapport_building,
                        "needs_discovery": needs_discovery,
                        "solution_presentation": solution_presentation,
                        "objection_handling": objection_handling,
                        "closing_technique": closing_technique,
                        "profile_understanding": profile_understanding,
                        "credibility_building": credibility_building,
                        "principles_usage": principles_usage,
                        "case_studies_usage": case_studies_usage,
                        "gap_creation": gap_creation,
                        "bhag_fine_tuning": bhag_fine_tuning,
                        "urgency_creation": urgency_creation,
                        "commitment_getting": commitment_getting,
                        "contextualisation": contextualisation,
                        "excitement_creation": excitement_creation
                    }
                    analysis = analyze_call_with_gpt(call_type, "", manual_scores)
                
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
                    "analysis_mode": analysis_mode,
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
                    st.metric("IL Compliance", f"{analysis['methodology_compliance']:.1f}%")
                with col3:
                    st.metric("Effectiveness", analysis['call_effectiveness'])
                with col4:
                    st.metric("Prediction", analysis['outcome_prediction']['likely_result'].replace('_', ' ').title())
                
                st.markdown("**Summary:**")
                st.info(analysis['call_summary'])
                
                # Core Dimensions
                st.markdown("### 🎯 Core Dimensions")
                core_df = pd.DataFrame([
                    {"Dimension": k.replace('_', ' ').title(), "Score": v, "Max": IRON_LADY_PARAMETERS["Core Quality Dimensions"][k]["weight"], "Percentage": f"{(v/IRON_LADY_PARAMETERS['Core Quality Dimensions'][k]['weight']*100):.0f}%"}
                    for k, v in analysis['core_dimensions'].items()
                ])
                st.dataframe(core_df, use_container_width=True, hide_index=True)
                
                # IL Parameters
                st.markdown("### 💎 Iron Lady Parameters")
                il_df = pd.DataFrame([
                    {"Parameter": k.replace('_', ' ').title(), "Score": v, "Max": 10, "Percentage": f"{(v/10*100):.0f}%"}
                    for k, v in analysis['iron_lady_parameters'].items()
                ])
                st.dataframe(il_df, use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### ✅ Strengths")
                    for s in analysis['key_insights']['strengths']:
                        st.success(f"✓ {s}")
                    
                    st.markdown("### 🌟 Best Moments")
                    for m in analysis['key_insights']['best_moments']:
                        st.write(f"⭐ {m}")
                
                with col2:
                    st.markdown("### 🔴 Critical Gaps")
                    for g in analysis['key_insights']['critical_gaps']:
                        st.error(f"✗ {g}")
                    
                    st.markdown("### ⚠️ Missed Opportunities")
                    for o in analysis['key_insights']['missed_opportunities']:
                        st.warning(f"→ {o}")
                
                st.markdown("### 💡 Coaching Recommendations")
                for rec in analysis['coaching_recommendations']:
                    st.write(f"🎯 {rec}")
                
                st.markdown("### 🎓 Iron Lady Coaching")
                for rec in analysis['iron_lady_specific_coaching']:
                    st.write(f"💎 {rec}")

# DASHBOARD PAGE
elif page == "Dashboard":
    st.title("📊 My Dashboard")
    
    rm_filter = st.text_input("Filter by your name", placeholder="Enter your name")
    call_type_filter = st.selectbox("Filter by Call Type", ["All"] + list(CALL_TYPE_FOCUS.keys()))
    
    db = load_db()
    
    if rm_filter:
        filtered_db = [record for record in db if rm_filter.lower() in record['rm_name'].lower()]
    else:
        filtered_db = db
    
    if call_type_filter != "All":
        filtered_db = [record for record in filtered_db if record.get('call_type') == call_type_filter]
    
    if not filtered_db:
        st.info("No calls found. Upload your first recording!")
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
        
        # Display calls
        st.markdown("---")
        st.subheader("📋 Call History")
        
        for record in reversed(filtered_db):
            analysis = record.get('analysis', {})
            with st.expander(
                f"📞 {record['call_type']} - {record['client_name']} - {record['call_date']} "
                f"(Score: {analysis.get('overall_score', 0):.1f}/100)"
            ):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**RM:** {record['rm_name']}")
                    st.write(f"**Participant:** {record['client_name']}")
                    st.write(f"**Call Type:** {record['call_type']}")
                    st.write(f"**Outcome:** {record['pitch_outcome']}")
                    st.write(f"**Duration:** {record.get('call_duration', 'N/A')} min")
                    st.write(f"**Analysis Mode:** {record.get('analysis_mode', 'N/A')}")
                    st.write(f"**Summary:** {analysis.get('call_summary', 'N/A')}")
                
                with col2:
                    st.metric("Score", f"{analysis.get('overall_score', 0):.1f}/100")
                    st.metric("IL Compliance", f"{analysis.get('methodology_compliance', 0):.1f}%")
                    st.write(f"**Effectiveness:** {analysis.get('call_effectiveness', 'N/A')}")
                
                st.markdown("**Top Strengths:**")
                for s in analysis.get('key_insights', {}).get('strengths', [])[:3]:
                    st.write(f"✓ {s}")
                
                st.markdown("**Critical Gaps:**")
                for g in analysis.get('key_insights', {}).get('critical_gaps', [])[:3]:
                    st.write(f"✗ {g}")
                
                # Delete button
                col_a, col_b = st.columns([1, 4])
                with col_a:
                    if st.button("🗑️ Delete", key=f"del_dash_{record['id']}"):
                        delete_record(record['id'])
                        st.success("Deleted!")
                        st.rerun()
                
                with col_b:
                    analysis_json = json.dumps(record, indent=2)
                    st.download_button(
                        label="📥 Download Analysis",
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
        for record in db:
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
        
        # Bulk delete option
        st.markdown("---")
        st.subheader("⚠️ Bulk Operations")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Delete All Records (Careful!)", type="secondary"):
                if st.checkbox("Confirm deletion of ALL records"):
                    save_db([])
                    st.success("All records deleted!")
                    st.rerun()
        
        with col2:
            # Download all data
            all_data_json = json.dumps(db, indent=2)
            st.download_button(
                label="📥 Backup All Data (JSON)",
                data=all_data_json,
                file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
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
                "ID": record['id'],
                "Date": record['call_date'],
                "RM Name": record['rm_name'],
                "Participant": record['client_name'],
                "Call Type": record.get('call_type', 'N/A'),
                "Duration": f"{record.get('call_duration', 'N/A')} min",
                "Outcome": record['pitch_outcome'],
                "Overall Score": f"{record['analysis'].get('overall_score', 0):.1f}",
                "IL Compliance": f"{record['analysis'].get('methodology_compliance', 0):.1f}%",
                "Effectiveness": record['analysis'].get('call_effectiveness', 'N/A'),
                "Mode": record.get('analysis_mode', 'N/A')
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Download CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"iron_lady_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            # Parameter Performance Analysis
            st.markdown("---")
            st.subheader("📊 Parameter Performance Analysis")
            
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
            
            if param_avg:
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
                st.info("💡 **Coaching Focus:** Prioritize 🔴 parameters for training")
            
            # Detailed records with delete
            st.markdown("---")
            st.subheader("🔍 Detailed Records")
            
            for record in reversed(filtered_db[:20]):
                analysis = record.get('analysis', {})
                with st.expander(
                    f"{record['rm_name']} - {record['call_type']} - {record['client_name']} ({record['call_date']}) "
                    f"- Score: {analysis.get('overall_score', 0):.1f}/100"
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Basic Info:**")
                        st.write(f"• Record ID: {record['id']}")
                        st.write(f"• RM: {record['rm_name']}")
                        st.write(f"• Participant: {record['client_name']}")
                        st.write(f"• Call Type: {record.get('call_type', 'N/A')}")
                        st.write(f"• Date: {record['call_date']}")
                        st.write(f"• Duration: {record.get('call_duration', 'N/A')} min")
                        st.write(f"• Outcome: {record['pitch_outcome']}")
                        st.write(f"• Analysis Mode: {record.get('analysis_mode', 'N/A')}")
                    
                    with col2:
                        st.write("**Performance:**")
                        st.write(f"• Overall Score: {analysis.get('overall_score', 0):.1f}/100")
                        st.write(f"• IL Compliance: {analysis.get('methodology_compliance', 0):.1f}%")
                        st.write(f"• Effectiveness: {analysis.get('call_effectiveness', 'N/A')}")
                        pred = analysis.get('outcome_prediction', {})
                        st.write(f"• Prediction: {pred.get('likely_result', 'N/A').replace('_', ' ').title()}")
                        st.write(f"• Confidence: {pred.get('confidence', 0)}%")
                    
                    st.write(f"**Summary:** {analysis.get('call_summary', 'N/A')}")
                    
                    if 'core_dimensions' in analysis:
                        st.write("**Core Dimensions:**")
                        for dim, score in analysis['core_dimensions'].items():
                            max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][dim]["weight"]
                            pct = (score / max_score) * 100
                            emoji = "🟢" if pct >= 80 else "🟡" if pct >= 60 else "🔴"
                            st.write(f"{emoji} {dim.replace('_', ' ').title()}: {score}/{max_score} ({pct:.0f}%)")
                    
                    if 'iron_lady_parameters' in analysis:
                        st.write("**Iron Lady Parameters:**")
                        for param, score in analysis['iron_lady_parameters'].items():
                            pct = (score / 10) * 100
                            emoji = "🟢" if pct >= 80 else "🟡" if pct >= 60 else "🔴"
                            st.write(f"{emoji} {param.replace('_', ' ').title()}: {score}/10 ({pct:.0f}%)")
                    
                    insights = analysis.get('key_insights', {})
                    if insights.get('strengths'):
                        st.write("**Strengths:**")
                        for s in insights['strengths'][:3]:
                            st.write(f"✓ {s}")
                    
                    if insights.get('critical_gaps'):
                        st.write("**Critical Gaps:**")
                        for g in insights['critical_gaps'][:3]:
                            st.write(f"✗ {g}")
                    
                    # Action buttons
                    col_a, col_b, col_c = st.columns([1, 1, 3])
                    with col_a:
                        if st.button("🗑️ Delete", key=f"del_admin_{record['id']}"):
                            if delete_record(record['id']):
                                st.success("Deleted!")
                                st.rerun()
                    
                    with col_b:
                        record_json = json.dumps(record, indent=2)
                        st.download_button(
                            label="📥 JSON",
                            data=record_json,
                            file_name=f"record_{record['id']}.json",
                            mime="application/json",
                            key=f"dl_admin_{record['id']}"
                        )

# Footer
st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Use GPT mode for consistent AI analysis or Manual mode for precise control!")
st.sidebar.markdown("**Iron Lady Framework**")
st.sidebar.markdown("• 27 Principles")
st.sidebar.markdown("• BHAG Focus")
st.sidebar.markdown("• Community Power")
st.sidebar.markdown("• Powerful Invites")
st.sidebar.markdown("---")
st.sidebar.markdown("Built for Iron Lady 👩‍💼")
