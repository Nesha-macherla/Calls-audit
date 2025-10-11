import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Iron Lady Call Analysis System",
    page_icon="👩‍💼",
    layout="wide"
)

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

def analyze_call_parameters(scores_dict, call_type):
    """
    Analyze call based on parameter scores provided by user
    No GPT dependency - pure calculation based on parameters
    """
    
    # Extract scores
    core_dims = {
        "rapport_building": scores_dict.get("rapport_building", 0),
        "needs_discovery": scores_dict.get("needs_discovery", 0),
        "solution_presentation": scores_dict.get("solution_presentation", 0),
        "objection_handling": scores_dict.get("objection_handling", 0),
        "closing_technique": scores_dict.get("closing_technique", 0)
    }
    
    il_params = {
        "profile_understanding": scores_dict.get("profile_understanding", 0),
        "credibility_building": scores_dict.get("credibility_building", 0),
        "principles_usage": scores_dict.get("principles_usage", 0),
        "case_studies_usage": scores_dict.get("case_studies_usage", 0),
        "gap_creation": scores_dict.get("gap_creation", 0),
        "bhag_fine_tuning": scores_dict.get("bhag_fine_tuning", 0),
        "urgency_creation": scores_dict.get("urgency_creation", 0),
        "commitment_getting": scores_dict.get("commitment_getting", 0),
        "contextualisation": scores_dict.get("contextualisation", 0),
        "excitement_creation": scores_dict.get("excitement_creation", 0)
    }
    
    # Calculate scores
    core_total = sum(core_dims.values())
    il_total = sum(il_params.values())
    
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
    
    # Generate insights based on scores
    strengths = []
    critical_gaps = []
    missed_opportunities = []
    best_moments = []
    
    # Analyze core dimensions
    for param, score in core_dims.items():
        max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][param]["weight"]
        percentage = (score / max_score) * 100
        param_name = param.replace('_', ' ').title()
        
        if percentage >= 80:
            strengths.append(f"Strong {param_name} ({score}/{max_score})")
            best_moments.append(f"Excellent execution of {param_name}")
        elif percentage < 50:
            critical_gaps.append(f"Weak {param_name} - scored only {score}/{max_score}")
            missed_opportunities.append(f"Need to improve {param_name} significantly")
    
    # Analyze IL parameters
    for param, score in il_params.items():
        percentage = (score / 10) * 100
        param_name = param.replace('_', ' ').title()
        
        if percentage >= 80:
            strengths.append(f"Strong {param_name} ({score}/10)")
        elif percentage < 50:
            critical_gaps.append(f"Weak {param_name} - scored only {score}/10")
            missed_opportunities.append(f"Leverage {param_name} more effectively")
    
    # Ensure we have at least some insights
    if not strengths:
        strengths = ["Some positive elements present", "Foundation established", "Room for significant growth"]
    if not critical_gaps:
        critical_gaps = ["Minor improvements needed", "Fine-tune execution", "Enhance consistency"]
    if not missed_opportunities:
        missed_opportunities = ["Optimize timing", "Deepen engagement", "Strengthen follow-through"]
    if not best_moments:
        best_moments = ["Professional approach maintained", "Key points covered", "Participant engaged"]
    
    # Generate coaching recommendations
    coaching_recommendations = []
    il_coaching = []
    
    # Focus on lowest scoring areas
    sorted_core = sorted(core_dims.items(), key=lambda x: x[1])
    sorted_il = sorted(il_params.items(), key=lambda x: x[1])
    
    for param, score in sorted_core[:2]:
        max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][param]["weight"]
        if score < max_score * 0.7:
            coaching_recommendations.append(
                f"Focus on improving {param.replace('_', ' ').title()} - currently at {score}/{max_score}"
            )
    
    for param, score in sorted_il[:3]:
        if score < 7:
            il_coaching.append(
                f"Strengthen {param.replace('_', ' ').title()} - aim for 8+/10 (currently {score}/10)"
            )
    
    # Add call-type specific coaching
    focus_areas = CALL_TYPE_FOCUS.get(call_type, [])
    for area in focus_areas[:2]:
        if area in il_params and il_params[area] < 7:
            il_coaching.append(
                f"Critical for {call_type}: Improve {area.replace('_', ' ').title()}"
            )
    
    # Ensure minimum recommendations
    if not coaching_recommendations:
        coaching_recommendations = [
            "Maintain current strengths",
            "Focus on consistency across all parameters",
            "Continue professional approach"
        ]
    
    if not il_coaching:
        il_coaching = [
            "Integrate more 27 Principles references",
            "Use specific case studies with names",
            "Deepen BHAG exploration",
            "Get explicit commitments"
        ]
    
    # Outcome prediction
    if overall_score >= 80 and il_params.get('commitment_getting', 0) >= 7 and il_params.get('bhag_fine_tuning', 0) >= 7:
        likely_result = "registration_expected"
        confidence = min(95, int(overall_score + 10))
        reasoning = "Strong overall performance with key commitments secured"
    elif overall_score >= 60:
        likely_result = "follow_up_needed"
        confidence = min(80, int(overall_score))
        reasoning = "Good foundation established, needs follow-up to secure commitment"
    else:
        likely_result = "needs_improvement"
        confidence = min(70, int(overall_score - 10))
        reasoning = "Significant gaps in methodology execution require attention"
    
    # Generate call summary
    summary = f"Call scored {overall_score:.1f}/100 with {methodology_compliance:.1f}% Iron Lady compliance. "
    if effectiveness == "Excellent":
        summary += "Outstanding execution across all parameters with strong methodology adherence."
    elif effectiveness == "Good":
        summary += "Solid performance with good methodology implementation and room for refinement."
    elif effectiveness == "Average":
        summary += "Acceptable execution but significant opportunities for improvement in key areas."
    else:
        summary += "Performance below standards - immediate coaching and practice required."
    
    return {
        "overall_score": round(overall_score, 1),
        "methodology_compliance": round(methodology_compliance, 1),
        "call_effectiveness": effectiveness,
        "core_dimensions": core_dims,
        "iron_lady_parameters": il_params,
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
st.sidebar.markdown("**Parameter-Based Analysis**")
st.sidebar.markdown("*Based on 27 Principles Framework*")
page = st.sidebar.radio("Navigate", ["Upload & Score", "Dashboard", "Admin View", "Parameters Guide"])

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
                
                # Scoring guide
                st.markdown("**Scoring Guide:**")
                weight = details['weight']
                if param == "rapport_building":
                    st.write(f"• 0-{int(weight*0.25)}: No greeting, cold, transactional")
                    st.write(f"• {int(weight*0.25)+1}-{int(weight*0.5)}: Basic greeting, minimal warmth")
                    st.write(f"• {int(weight*0.5)+1}-{int(weight*0.75)}: Good greeting, some personalization")
                    st.write(f"• {int(weight*0.75)+1}-{weight}: Excellent greeting, high empathy, strong relatedness")
                elif param == "needs_discovery":
                    st.write(f"• 0-{int(weight*0.24)}: 0-2 questions asked")
                    st.write(f"• {int(weight*0.24)+1}-{int(weight*0.48)}: 3-4 basic questions")
                    st.write(f"• {int(weight*0.48)+1}-{int(weight*0.72)}: 5-7 strategic questions")
                    st.write(f"• {int(weight*0.72)+1}-{weight}: 8+ strategic questions with deep BHAG exploration")
                elif param == "solution_presentation":
                    st.write(f"• 0-{int(weight*0.24)}: Program barely mentioned")
                    st.write(f"• {int(weight*0.24)+1}-{int(weight*0.48)}: Basic program mention")
                    st.write(f"• {int(weight*0.48)+1}-{int(weight*0.72)}: Good explanation with benefits")
                    st.write(f"• {int(weight*0.72)+1}-{weight}: Comprehensive presentation with social proof")
    
    with tab2:
        st.subheader("💎 Iron Lady Specific Parameters (100 points)")
        for param, details in IRON_LADY_PARAMETERS["Iron Lady Specific Parameters"].items():
            with st.expander(f"**{param.replace('_', ' ').title()}** ({details['weight']} points)"):
                st.write(f"**Description:** {details['description']}")
                st.write(f"**Weight:** {details['weight']} points")
                st.markdown("**Scoring Guide (0-10):**")
                st.write("• 0-3: Not mentioned or very weak")
                st.write("• 4-6: Mentioned briefly or basic")
                st.write("• 7-8: Good usage with context")
                st.write("• 9-10: Excellent usage, specific, impactful")
    
    with tab3:
        st.subheader("📋 Call Type Specific Focus Areas")
        for call_type, params in CALL_TYPE_FOCUS.items():
            with st.expander(f"**{call_type}**"):
                st.write("**Focus on these parameters:**")
                for param in params:
                    st.write(f"• {param.replace('_', ' ').title()}")

# UPLOAD PAGE
elif page == "Upload & Score":
    st.title("📤 Upload Call & Score Parameters")
    st.write("Upload your recording and score each parameter based on actual call performance")
    
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
        
        # Show relevant parameters for selected call type
        st.markdown(f"### 📋 Score Parameters for {call_type}")
        st.info(f"💡 Focus on: {', '.join([p.replace('_', ' ').title() for p in CALL_TYPE_FOCUS.get(call_type, [])[:5]])}")
        
        st.markdown("---")
        st.markdown("### 🎯 Core Quality Dimensions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            rapport_building = st.slider(
                "Rapport Building",
                0, 20, 10,
                help="Greetings, warmth, empathy, personalization (0-20)"
            )
            
            needs_discovery = st.slider(
                "Needs Discovery",
                0, 25, 12,
                help="Strategic questions, understanding challenges and BHAG (0-25)"
            )
            
            solution_presentation = st.slider(
                "Solution Presentation",
                0, 25, 12,
                help="Program benefits, community value, outcomes (0-25)"
            )
        
        with col2:
            objection_handling = st.slider(
                "Objection Handling",
                0, 15, 8,
                help="Concern handling with empathy and solutions (0-15)"
            )
            
            closing_technique = st.slider(
                "Closing Technique",
                0, 15, 8,
                help="Powerful invite, next steps, commitment (0-15)"
            )
        
        st.markdown("---")
        st.markdown("### 💎 Iron Lady Specific Parameters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            profile_understanding = st.slider("Profile Understanding", 0, 10, 5, help="Experience, role, challenges, goals")
            credibility_building = st.slider("Credibility Building", 0, 10, 5, help="Iron Lady community, success stories")
            principles_usage = st.slider("27 Principles Usage", 0, 10, 5, help="Principles mentioned by name")
            case_studies_usage = st.slider("Case Studies Usage", 0, 10, 5, help="Specific success stories with names")
        
        with col2:
            gap_creation = st.slider("Gap Creation", 0, 10, 5, help="Highlighting what's missing for BHAG")
            bhag_fine_tuning = st.slider("BHAG Fine Tuning", 0, 10, 5, help="Making them dream bigger")
            urgency_creation = st.slider("Urgency Creation", 0, 10, 5, help="Limited spots, immediate action")
            commitment_getting = st.slider("Commitment Getting", 0, 10, 5, help="Explicit commitments obtained")
        
        with col3:
            contextualisation = st.slider("Contextualisation", 0, 10, 5, help="Personalizing to their situation")
            excitement_creation = st.slider("Excitement Creation", 0, 10, 5, help="Creating enthusiasm about journey")
        
        notes = st.text_area(
            "Additional Notes (Optional)",
            placeholder="Any specific observations during the call..."
        )
        
        submitted = st.form_submit_button("🚀 Generate Analysis", use_container_width=True)
    
    if submitted:
        if not all([rm_name, client_name, uploaded_file]):
            st.error("❌ Please fill in all required fields (*)")
        else:
            with st.spinner(f"🔄 Analyzing your {call_type}..."):
                # Save uploaded file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_extension = uploaded_file.name.split('.')[-1]
                filename = f"{rm_name.replace(' ', '_')}_{call_type.replace(' ', '_')}_{timestamp}.{file_extension}"
                file_path = UPLOADS_DIR / filename
                
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                
                # Analyze based on parameters
                scores_dict = {
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
                
                analysis = analyze_call_parameters(scores_dict, call_type)
                
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
                    st.metric("Prediction", analysis['outcome_prediction']['likely_result'].replace('_', ' ').title())
                
                st.markdown("**Executive Summary:**")
                st.info(analysis['call_summary'])
                
                # Core Dimensions Breakdown
                st.markdown("### 🎯 Core Quality Dimensions")
                core_dims = analysis.get('core_dimensions', {})
                if core_dims:
                    core_df = pd.DataFrame([
                        {"Dimension": k.replace('_', ' ').title(), "Score": v, "Max": IRON_LADY_PARAMETERS["Core Quality Dimensions"][k]["weight"], "Percentage": f"{(v/IRON_LADY_PARAMETERS['Core Quality Dimensions'][k]['weight']*100):.1f}%"}
                        for k, v in core_dims.items()
                    ])
                    st.dataframe(core_df, use_container_width=True, hide_index=True)
                
                # Iron Lady Parameters Breakdown
                st.markdown("### 💎 Iron Lady Specific Parameters")
                il_params = analysis.get('iron_lady_parameters', {})
                if il_params:
                    il_df = pd.DataFrame([
                        {"Parameter": k.replace('_', ' ').title(), "Score": v, "Max": 10, "Percentage": f"{(v/10*100):.1f}%"}
                        for k, v in il_params.items()
                    ])
                    st.dataframe(il_df, use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### ✅ Strengths")
                    for strength in analysis.get('key_insights', {}).get('strengths', []):
                        st.success(f"✓ {strength}")
                    
                    st.markdown("### 🌟 Best Moments")
                    for moment in analysis.get('key_insights', {}).get('best_moments', []):
                        st.write(f"⭐ {moment}")
                
                with col2:
                    st.markdown("### 🔴 Critical Gaps")
                    for gap in analysis.get('key_insights', {}).get('critical_gaps', []):
                        st.error(f"✗ {gap}")
                    
                    st.markdown("### ⚠️ Missed Opportunities")
                    for opp in analysis.get('key_insights', {}).get('missed_opportunities', []):
                        st.warning(f"→ {opp}")
                
                st.markdown("### 💡 General Coaching Recommendations")
                for rec in analysis.get('coaching_recommendations', []):
                    st.write(f"🎯 {rec}")
                
                st.markdown("### 🎓 Iron Lady Specific Coaching")
                for rec in analysis.get('iron_lady_specific_coaching', []):
                    st.write(f"💎 {rec}")
                
                # Outcome Prediction
                st.markdown("### 🔮 Outcome Prediction")
                pred = analysis.get('outcome_prediction', {})
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Likely Result", pred.get('likely_result', 'N/A').replace('_', ' ').title())
                with col2:
                    st.metric("Confidence", f"{pred.get('confidence', 0)}%")
                with col3:
                    st.write(f"**Reasoning:** {pred.get('reasoning', 'N/A')}")

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
                    st.write(f"**Summary:** {analysis.get('call_summary', 'No summary available')}")
                
                with col2:
                    st.metric("Overall Score", f"{analysis.get('overall_score', 0):.1f}/100")
                    st.metric("IL Compliance", f"{analysis.get('methodology_compliance', 0):.1f}%")
                    st.write(f"**Effectiveness:** {analysis.get('call_effectiveness', 'N/A')}")
                    pred = analysis.get('outcome_prediction', {})
                    st.write(f"**Prediction:** {pred.get('likely_result', 'N/A').replace('_', ' ').title()}")
                
                st.markdown("**Top Strengths:**")
                strengths = record.get('analysis', {}).get('key_insights', {}).get('strengths', [])
                for item in strengths[:3]:
                    st.write(f"✓ {item}")
                
                st.markdown("**Critical Gaps:**")
                gaps = record.get('analysis', {}).get('key_insights', {}).get('critical_gaps', [])
                for item in gaps[:3]:
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
                
                st.info("💡 **Coaching Focus:** Prioritize parameters marked 🔴 Needs Work for team training")
            else:
                st.info("No Iron Lady parameter data available for selected filters")
            
            # Detailed view
            st.markdown("---")
            st.subheader("🔍 Detailed Records")
            
            for record in reversed(filtered_db[:10]):
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
                    
                    if 'core_dimensions' in record['analysis']:
                        st.write("**Core Dimensions:**")
                        for dim, score in record['analysis']['core_dimensions'].items():
                            max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][dim]["weight"]
                            percentage = (score / max_score) * 100
                            emoji = "🟢" if percentage >= 80 else "🟡" if percentage >= 60 else "🔴"
                            st.write(f"{emoji} {dim.replace('_', ' ').title()}: {score}/{max_score} ({percentage:.0f}%)")
                    
                    if 'iron_lady_parameters' in record['analysis']:
                        st.write("**Iron Lady Parameters:**")
                        for param, score in record['analysis']['iron_lady_parameters'].items():
                            percentage = (score / 10) * 100
                            emoji = "🟢" if percentage >= 80 else "🟡" if percentage >= 60 else "🔴"
                            st.write(f"{emoji} {param.replace('_', ' ').title()}: {score}/10 ({percentage:.0f}%)")
                    
                    insights = record['analysis'].get('key_insights', {})
                    if insights.get('strengths'):
                        st.write("**Strengths:**")
                        for s in insights['strengths']:
                            st.write(f"✓ {s}")
                    
                    if insights.get('critical_gaps'):
                        st.write("**Critical Gaps:**")
                        for g in insights['critical_gaps']:
                            st.write(f"✗ {g}")
                    
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
st.sidebar.info("💡 **Tip:** Score parameters honestly based on actual call performance!")
st.sidebar.markdown("**Iron Lady Framework**")
st.sidebar.markdown("• 27 Principles")
st.sidebar.markdown("• BHAG Focus")
st.sidebar.markdown("• Community Power")
st.sidebar.markdown("• Powerful Invites")
st.sidebar.markdown("---")
st.sidebar.markdown("Built for Iron Lady 👩‍💼")
