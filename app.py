import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import openai
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

# Page configuration
st.set_page_config(
    page_title="Iron Lady Call Analysis System",
    page_icon="👩‍💼",
    layout="wide"
)

# Initialize OpenAI client
openai.api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

# AWS S3 Functions
def get_s3_client():
    """Initialize S3 client"""
    try:
        return boto3.client(
            's3',
            aws_access_key_id=st.secrets.get("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID")),
            aws_secret_access_key=st.secrets.get("AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY")),
            region_name=st.secrets.get("AWS_S3_REGION", os.getenv("AWS_S3_REGION", "ap-south-1"))
        )
    except Exception as e:
        return None

def get_bucket_name():
    return st.secrets.get("AWS_S3_BUCKET_NAME", os.getenv("AWS_S3_BUCKET_NAME"))

def upload_to_s3(file_obj, filename, metadata=None):
    """Upload file to S3"""
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()
    
    if not s3_client or not bucket_name:
        return None
    
    try:
        date_path = datetime.now().strftime("%Y/%m/%d")
        s3_key = f"recordings/{date_path}/{filename}"
        
        ext = Path(filename).suffix.lower()
        content_types = {'.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.m4a': 'audio/mp4', '.mp4': 'video/mp4'}
        
        extra_args = {
            'ContentType': content_types.get(ext, 'application/octet-stream'),
            'ServerSideEncryption': 'AES256'
        }
        
        if metadata:
            extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}
        
        file_obj.seek(0)
        s3_client.upload_fileobj(file_obj, bucket_name, s3_key, ExtraArgs=extra_args)
        
        return f"s3://{bucket_name}/{s3_key}"
    except Exception as e:
        st.error(f"S3 upload failed: {str(e)}")
        return None

def setup_s3_lifecycle():
    """Setup 7-day auto-delete"""
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()
    
    if not s3_client or not bucket_name:
        return False
    
    try:
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration={
                'Rules': [{
                    'Id': 'DeleteRecordingsAfter7Days',
                    'Status': 'Enabled',
                    'Prefix': 'recordings/',
                    'Expiration': {'Days': 7}
                }]
            }
        )
        return True
    except:
        return False

def get_s3_stats():
    """Get S3 statistics"""
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()
    
    if not s3_client or not bucket_name:
        return None
    
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix='recordings/')
        total_size = 0
        file_count = 0
        
        if 'Contents' in response:
            for obj in response['Contents']:
                total_size += obj['Size']
                file_count += 1
        
        size_mb = total_size / (1024 * 1024)
        size_gb = size_mb / 1024
        
        return {
            'size': f"{size_gb:.2f} GB" if size_gb > 1 else f"{size_mb:.2f} MB",
            'files': file_count
        }
    except:
        return None

def generate_summary_report(record):
    """Generate downloadable summary with improvements"""
    analysis = record.get('analysis', {})
    
    report = f"""
╔══════════════════════════════════════════════════════════════════╗
║         IRON LADY CALL ANALYSIS - SUMMARY REPORT                ║
╚══════════════════════════════════════════════════════════════════╝

📋 CALL DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RM Name:           {record.get('rm_name', 'N/A')}
Participant:       {record.get('client_name', 'N/A')}
Call Type:         {record.get('call_type', 'N/A')}
Date:              {record.get('call_date', 'N/A')}
Duration:          {record.get('call_duration', 'N/A')} minutes
Outcome:           {record.get('pitch_outcome', 'N/A')}
Analysis Mode:     {record.get('analysis_mode', 'N/A')}

📊 PERFORMANCE SCORES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Score:           {analysis.get('overall_score', 0):.1f}/100
Iron Lady Compliance:    {analysis.get('methodology_compliance', 0):.1f}%
Call Effectiveness:      {analysis.get('call_effectiveness', 'N/A')}

🎯 CORE QUALITY DIMENSIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    core_dims = analysis.get('core_dimensions', {})
    weights = {"rapport_building": 20, "needs_discovery": 25, "solution_presentation": 25, "objection_handling": 15, "closing_technique": 15}
    for dim, score in core_dims.items():
        max_score = weights.get(dim, 10)
        pct = (score / max_score) * 100
        status = "✓" if pct >= 70 else "⚠" if pct >= 50 else "✗"
        report += f"{status} {dim.replace('_', ' ').title():<25} {score:>2}/{max_score:<2} ({pct:>3.0f}%)\n"
    
    report += f"""
💎 IRON LADY SPECIFIC PARAMETERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    il_params = analysis.get('iron_lady_parameters', {})
    for param, score in il_params.items():
        pct = (score / 10) * 100
        status = "✓" if pct >= 70 else "⚠" if pct >= 50 else "✗"
        report += f"{status} {param.replace('_', ' ').title():<25} {score:>2}/10 ({pct:>3.0f}%)\n"
    
    report += f"""
✅ KEY STRENGTHS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for i, s in enumerate(analysis.get('key_insights', {}).get('strengths', []), 1):
        report += f"{i}. {s}\n"
    
    report += f"""
🔴 CRITICAL IMPROVEMENT AREAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for i, g in enumerate(analysis.get('key_insights', {}).get('critical_gaps', []), 1):
        report += f"{i}. {g}\n"
    
    report += f"""
⚠️ MISSED OPPORTUNITIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for i, o in enumerate(analysis.get('key_insights', {}).get('missed_opportunities', []), 1):
        report += f"{i}. {o}\n"
    
    report += f"""
💡 COACHING RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for i, r in enumerate(analysis.get('coaching_recommendations', []), 1):
        report += f"{i}. {r}\n"
    
    report += f"""
🎓 IRON LADY SPECIFIC COACHING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for i, r in enumerate(analysis.get('iron_lady_specific_coaching', []), 1):
        report += f"{i}. {r}\n"
    
    report += f"""
🔮 OUTCOME PREDICTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Prediction:    {analysis.get('outcome_prediction', {}).get('likely_result', 'N/A').replace('_', ' ').title()}
Confidence:    {analysis.get('outcome_prediction', {}).get('confidence', 0)}%
Reasoning:     {analysis.get('outcome_prediction', {}).get('reasoning', 'N/A')}

📝 EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{analysis.get('call_summary', 'N/A')}

═══════════════════════════════════════════════════════════════════
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Iron Lady Call Analysis System - AWS S3 Storage Enabled
Files auto-delete after 7 days
═══════════════════════════════════════════════════════════════════
"""
    return report

# Create data directory (database only, not uploads)
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DB_FILE = DATA_DIR / "calls_database.json"

# Iron Lady Parameters (keeping your existing structure)
IRON_LADY_PARAMETERS = {
    "Core Quality Dimensions": {
        "rapport_building": {"weight": 20, "description": "Greetings, warmth, empathy, personalization, relatedness"},
        "needs_discovery": {"weight": 25, "description": "Strategic questions, probing, understanding challenges and BHAG"},
        "solution_presentation": {"weight": 25, "description": "Program benefits, community value, outcomes, social proof"},
        "objection_handling": {"weight": 15, "description": "Concern handling with empathy and solutions"},
        "closing_technique": {"weight": 15, "description": "Powerful invite, next steps, commitment getting"}
    },
    "Iron Lady Specific Parameters": {
        "profile_understanding": {"weight": 10, "description": "Understanding experience, role, challenges, goals"},
        "credibility_building": {"weight": 10, "description": "Iron Lady community, success stories, mentors, certification"},
        "principles_usage": {"weight": 10, "description": "27 Principles framework (Unpredictable Behaviour, 10000 Hours, Differentiate Branding, Shameless Pitching, Art of Negotiation, Contextualisation)"},
        "case_studies_usage": {"weight": 10, "description": "Success stories from participants (Neha, Rashmi, Chandana, Annapurna, Pushpalatha, Tejaswini)"},
        "gap_creation": {"weight": 10, "description": "Highlighting what's missing to achieve BHAG, creating urgency"},
        "bhag_fine_tuning": {"weight": 10, "description": "Big Hairy Audacious Goal exploration, making them dream bigger"},
        "urgency_creation": {"weight": 10, "description": "Limited spots, immediate action, cost of inaction"},
        "commitment_getting": {"weight": 10, "description": "Explicit commitments for attendance, participation, taking calls"},
        "contextualisation": {"weight": 10, "description": "Personalizing to participant's specific situation and profile"},
        "excitement_creation": {"weight": 10, "description": "Creating enthusiasm about transformation journey"}
    }
}

CALL_TYPE_FOCUS = {
    "Welcome Call": ["rapport_building", "profile_understanding", "credibility_building", "principles_usage", "case_studies_usage", "gap_creation", "bhag_fine_tuning", "commitment_getting", "urgency_creation", "contextualisation", "excitement_creation"],
    "BHAG Call": ["bhag_fine_tuning", "gap_creation", "case_studies_usage", "commitment_getting", "principles_usage", "urgency_creation", "closing_technique"],
    "Registration Call": ["urgency_creation", "objection_handling", "commitment_getting", "solution_presentation", "credibility_building", "closing_technique"],
    "30 Sec Pitch": ["profile_understanding", "gap_creation", "case_studies_usage", "urgency_creation", "commitment_getting", "excitement_creation"],
    "Second Level Call": ["credibility_building", "objection_handling", "solution_presentation", "case_studies_usage", "commitment_getting"],
    "Follow Up Call": ["commitment_getting", "objection_handling", "urgency_creation", "case_studies_usage", "closing_technique"]
}

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
    db = load_db()
    db = [r for r in db if r['id'] != record_id]
    save_db(db)
    return True

def analyze_call_with_gpt(call_type, additional_context, manual_scores=None):
    """Hybrid analysis: GPT or manual scores"""
    try:
        if manual_scores:
            return generate_analysis_from_scores(manual_scores, call_type, "Manual scoring with GPT-generated insights")
        
        focus_areas = CALL_TYPE_FOCUS.get(call_type, [])
        
        prompt = f"""You are an expert Iron Lady sales call analyst. Analyze this {call_type} and provide scores.

**CALL CONTEXT:**
{additional_context}

**CRITICAL: Provide REALISTIC scores based on actual content. Do NOT give default 50% scores.**

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
    "justification": "Brief explanation"
}}
"""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert call analyst. Provide realistic scores. Be strict but fair."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        analysis_text = response.choices[0].message.content
        scores_data = json.loads(analysis_text)
        
        return generate_analysis_from_scores(
            scores_data.get('core_dimensions', {}),
            call_type,
            scores_data.get('justification', 'GPT analysis'),
            scores_data.get('iron_lady_parameters', {})
        )
    except Exception as e:
        st.error(f"GPT Error: {str(e)}")
        return generate_analysis_from_scores({
            "rapport_building": 10, "needs_discovery": 12, "solution_presentation": 12,
            "objection_handling": 8, "closing_technique": 8
        }, call_type, f"Error: {str(e)}")

def generate_analysis_from_scores(core_dims, call_type, justification, il_params=None):
    """Generate complete analysis from scores"""
    
    core_dimensions = {
        "rapport_building": core_dims.get("rapport_building", 10),
        "needs_discovery": core_dims.get("needs_discovery", 12),
        "solution_presentation": core_dims.get("solution_presentation", 12),
        "objection_handling": core_dims.get("objection_handling", 8),
        "closing_technique": core_dims.get("closing_technique", 8)
    }
    
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
    
    core_total = sum(core_dimensions.values())
    il_total = sum(iron_lady_parameters.values())
    
    overall_score = (core_total * 0.6) + (il_total * 0.4)
    methodology_compliance = il_total
    
    if overall_score >= 85:
        effectiveness = "Excellent"
    elif overall_score >= 70:
        effectiveness = "Good"
    elif overall_score >= 50:
        effectiveness = "Average"
    else:
        effectiveness = "Needs Improvement"
    
    strengths = []
    critical_gaps = []
    missed_opportunities = []
    best_moments = []
    
    for param, score in core_dimensions.items():
        max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][param]["weight"]
        pct = (score / max_score) * 100
        param_name = param.replace('_', ' ').title()
        
        if pct >= 80:
            strengths.append(f"Strong {param_name} - {score}/{max_score} ({pct:.0f}%)")
            best_moments.append(f"Excellent {param_name}")
        elif pct < 50:
            critical_gaps.append(f"Weak {param_name} - {score}/{max_score}")
            missed_opportunities.append(f"Improve {param_name}")
    
    for param, score in iron_lady_parameters.items():
        pct = (score / 10) * 100
        param_name = param.replace('_', ' ').title()
        
        if pct >= 80:
            strengths.append(f"Strong {param_name} - {score}/10")
        elif pct < 50:
            critical_gaps.append(f"Weak {param_name} - {score}/10")
            missed_opportunities.append(f"Improve {param_name}")
    
    if not strengths:
        strengths = ["Professional approach"]
    if not critical_gaps:
        critical_gaps = ["Fine-tune delivery"]
    if not missed_opportunities:
        missed_opportunities = ["Deepen engagement"]
    if not best_moments:
        best_moments = ["Call completed"]
    
    coaching_recommendations = []
    il_coaching = []
    
    sorted_core = sorted(core_dimensions.items(), key=lambda x: x[1])
    sorted_il = sorted(iron_lady_parameters.items(), key=lambda x: x[1])
    
    for param, score in sorted_core[:3]:
        max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][param]["weight"]
        if score < max_score * 0.7:
            coaching_recommendations.append(f"Improve {param.replace('_', ' ').title()} to {int(max_score*0.8)}/{max_score}")
    
    for param, score in sorted_il[:4]:
        if score < 7:
            il_coaching.append(f"{param.replace('_', ' ').title()} needs work (target: 8+/10)")
    
    if not coaching_recommendations:
        coaching_recommendations = ["Maintain current performance"]
    if not il_coaching:
        il_coaching = ["Integrate more 27 Principles"]
    
    commit_score = iron_lady_parameters.get('commitment_getting', 0)
    bhag_score = iron_lady_parameters.get('bhag_fine_tuning', 0)
    
    if overall_score >= 80 and commit_score >= 7 and bhag_score >= 7:
        likely_result = "registration_expected"
        confidence = min(95, int(overall_score + 5))
        reasoning = f"Strong performance ({overall_score:.0f}/100)"
    elif overall_score >= 60:
        likely_result = "follow_up_needed"
        confidence = min(80, int(overall_score - 5))
        reasoning = f"Moderate performance ({overall_score:.0f}/100)"
    else:
        likely_result = "needs_improvement"
        confidence = min(70, int(overall_score - 15))
        reasoning = f"Below standard ({overall_score:.0f}/100)"
    
    summary = f"{call_type} scored {overall_score:.1f}/100 with {methodology_compliance:.1f}% IL compliance. {justification}"
    
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

# Sidebar
st.sidebar.title("👩‍💼 Iron Lady Call Analysis")
st.sidebar.markdown("**Hybrid GPT + Manual Analysis**")
st.sidebar.markdown("*Based on 27 Principles Framework*")

# S3 Status
st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 AWS S3 Storage")
try:
    stats = get_s3_stats()
    if stats:
        st.sidebar.success("**Connected** ✅")
        st.sidebar.info(f"**Files:** {stats['files']}\n**Size:** {stats['size']}")
        st.sidebar.caption("🗑️ Auto-delete: 7 days")
        
        if st.sidebar.button("⚙️ Setup Auto-Delete"):
            if setup_s3_lifecycle():
                st.sidebar.success("✅ Configured!")
            else:
                st.sidebar.warning("May already be set")
    else:
        st.sidebar.warning("S3 stats unavailable")
except:
    st.sidebar.error("⚠️ S3 not configured")
    st.sidebar.caption("Add AWS credentials to secrets")

page = st.sidebar.radio("Navigate", ["Upload & Analyze", "Dashboard", "Admin View", "Parameters Guide"])

# Parameters Guide Page
if page == "Parameters Guide":
    st.title("📚 Iron Lady Parameters Guide")
    tab1, tab2, tab3 = st.tabs(["Core Dimensions", "Iron Lady Parameters", "Call Type Focus"])
    
    with tab1:
        st.subheader("🎯 Core Quality Dimensions")
        for param, details in IRON_LADY_PARAMETERS["Core Quality Dimensions"].items():
            with st.expander(f"**{param.replace('_', ' ').title()}** ({details['weight']} pts)"):
                st.write(f"**Description:** {details['description']}")
    
    with tab2:
        st.subheader("💎 Iron Lady Parameters")
        for param, details in IRON_LADY_PARAMETERS["Iron Lady Specific Parameters"].items():
            with st.expander(f"**{param.replace('_', ' ').title()}** ({details['weight']} pts)"):
                st.write(f"**Description:** {details['description']}")
    
    with tab3:
        st.subheader("📋 Call Type Focus")
        for call_type, params in CALL_TYPE_FOCUS.items():
            with st.expander(f"**{call_type}**"):
                for param in params:
                    st.write(f"• {param.replace('_', ' ').title()}")

# Upload Page
elif page == "Upload & Analyze":
    st.title("📤 Upload Call & Get AI Analysis")
    
    analysis_mode = st.radio("Analysis Mode:", ["🤖 GPT Auto-Analysis (Recommended)", "✍️ Manual Scoring"], horizontal=True)
    
    with st.form("upload_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            rm_name = st.text_input("RM Name *")
            client_name = st.text_input("Participant Name *")
            call_type = st.selectbox("Call Type *", list(CALL_TYPE_FOCUS.keys()))
        
        with col2:
            pitch_outcome = st.selectbox("Call Outcome *", ["Success - Committed", "Partial - Needs Follow-up", "Not Interested", "Rescheduled"])
            call_date = st.date_input("Call Date *", datetime.now())
            call_duration = st.number_input("Call Duration (minutes)", 1, 120, 15)
        
        uploaded_file = st.file_uploader("Upload Recording *", type=['mp3', 'wav', 'm4a', 'mp4'])
        
        st.markdown(f"### 📋 Key Focus for {call_type}")
        focus_params = CALL_TYPE_FOCUS.get(call_type, [])
        st.info("✓ " + " • ".join([p.replace('_', ' ').title() for p in focus_params[:5]]))
        
        if "GPT" in analysis_mode:
            additional_context = st.text_area("Call Summary * (For GPT)", placeholder="Describe what happened...", height=200)
        else:
            additional_context = ""
            st.info("💡 Manual mode: Score each parameter")
            
            st.markdown("### 🎯 Core Dimensions")
            col1, col2 = st.columns(2)
            with col1:
                rapport_building = st.slider("Rapport Building", 0, 20, 10)
                needs_discovery = st.slider("Needs Discovery", 0, 25, 12)
                solution_presentation = st.slider("Solution Presentation", 0, 25, 12)
            with col2:
                objection_handling = st.slider("Objection Handling", 0, 15, 8)
                closing_technique = st.slider("Closing Technique", 0, 15, 8)
            
            st.markdown("### 💎 Iron Lady Parameters")
            col1, col2, col3 = st.columns(3)
            with col1:
                profile_understanding = st.slider("Profile Understanding", 0, 10, 5)
                credibility_building = st.slider("Credibility Building", 0, 10, 5)
                principles_usage = st.slider("Principles Usage", 0, 10, 5)
            with col2:
                case_studies_usage = st.slider("Case Studies", 0, 10, 5)
                gap_creation = st.slider("Gap Creation", 0, 10, 5)
                bhag_fine_tuning = st.slider("BHAG Fine Tuning", 0, 10, 5)
            with col3:
                urgency_creation = st.slider("Urgency Creation", 0, 10, 5)
                commitment_getting = st.slider("Commitment Getting", 0, 10, 5)
                contextualisation = st.slider("Contextualisation", 0, 10, 5)
            excitement_creation = st.slider("Excitement Creation", 0, 10, 5)
        
        notes = st.text_area("Additional Notes (Optional)")
        submitted = st.form_submit_button("🚀 Analyze Call", use_container_width=True)
    
    if submitted:
        if not all([rm_name, client_name, uploaded_file]):
            st.error("❌ Please fill all required fields (*)")
        elif "GPT" in analysis_mode and len(additional_context.strip()) < 100:
            st.error("❌ Provide detailed call summary (min 100 chars)")
        else:
            with st.spinner(f"🔄 Uploading to S3 and analyzing..."):
                # Upload to S3
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_extension = uploaded_file.name.split('.')[-1]
                filename = f"{rm_name.replace(' ', '_')}_{call_type.replace(' ', '_')}_{timestamp}.{file_extension}"
                
                metadata = {
                    'rm_name': rm_name,
                    'client_name': client_name,
                    'call_type': call_type,
                    'uploaded_date': datetime.now().isoformat()
                }
                
                s3_url = upload_to_s3(uploaded_file, filename, metadata=metadata)
                
                if not s3_url:
                    st.error("❌ S3 upload failed. Check AWS configuration in Streamlit secrets.")
                    st.stop()
                
                st.success(f"✅ File uploaded to S3 (auto-deletes in 7 days)")
                
                # Analyze
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
                    "file_path": s3_url,
                    "file_name": uploaded_file.name,
                    "storage_type": "s3",
                    "expires_at": (datetime.now().timestamp() + (7 * 24 * 60 * 60)),
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
                    {"Dimension": k.replace('_', ' ').title(), "Score": v, 
                     "Max": IRON_LADY_PARAMETERS["Core Quality Dimensions"][k]["weight"],
                     "Percentage": f"{(v/IRON_LADY_PARAMETERS['Core Quality Dimensions'][k]['weight']*100):.0f}%"}
                    for k, v in analysis['core_dimensions'].items()
                ])
                st.dataframe(core_df, use_container_width=True, hide_index=True)
                
                # IL Parameters
                st.markdown("### 💎 Iron Lady Parameters")
                il_df = pd.DataFrame([
                    {"Parameter": k.replace('_', ' ').title(), "Score": v, "Max": 10,
                     "Percentage": f"{(v/10*100):.0f}%"}
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

# Dashboard Page
elif page == "Dashboard":
    st.title("📊 My Dashboard")
    
    rm_filter = st.text_input("Filter by your name")
    call_type_filter = st.selectbox("Filter by Call Type", ["All"] + list(CALL_TYPE_FOCUS.keys()))
    
    db = load_db()
    
    filtered_db = [r for r in db if not rm_filter or rm_filter.lower() in r['rm_name'].lower()]
    if call_type_filter != "All":
        filtered_db = [r for r in filtered_db if r.get('call_type') == call_type_filter]
    
    if not filtered_db:
        st.info("No calls found. Upload your first recording!")
    else:
        st.write(f"**Total Calls:** {len(filtered_db)}")
        
        success_rate = len([r for r in filtered_db if "Success" in r['pitch_outcome']]) / len(filtered_db) * 100
        avg_score = sum([r['analysis'].get('overall_score', 0) for r in filtered_db]) / len(filtered_db)
        avg_compliance = sum([r['analysis'].get('methodology_compliance', 0) for r in filtered_db]) / len(filtered_db)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Success Rate", f"{success_rate:.1f}%")
        with col2:
            st.metric("Avg Score", f"{avg_score:.1f}/100")
        with col3:
            st.metric("Avg IL Compliance", f"{avg_compliance:.1f}%")
        with col4:
            st.metric("Total Calls", len(filtered_db))
        
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
                    st.write(f"**Storage:** {record.get('storage_type', 'local')}")
                    st.write(f"**Summary:** {analysis.get('call_summary', 'N/A')}")
                
                with col2:
                    st.metric("Score", f"{analysis.get('overall_score', 0):.1f}/100")
                    st.metric("IL Compliance", f"{analysis.get('methodology_compliance', 0):.1f}%")
                
                st.markdown("**Top Strengths:**")
                for s in analysis.get('key_insights', {}).get('strengths', [])[:3]:
                    st.write(f"✓ {s}")
                
                st.markdown("**Critical Gaps:**")
                for g in analysis.get('key_insights', {}).get('critical_gaps', [])[:3]:
                    st.write(f"✗ {g}")
                
                # Action buttons
                col_a, col_b, col_c = st.columns([1, 1, 2])
                with col_a:
                    if st.button("🗑️ Delete", key=f"del_dash_{record['id']}"):
                        delete_record(record['id'])
                        st.success("Deleted!")
                        st.rerun()
                
                with col_b:
                    summary_report = generate_summary_report(record)
                    st.download_button(
                        label="📄 Summary",
                        data=summary_report,
                        file_name=f"summary_{record['rm_name']}_{record['call_date']}.txt",
                        mime="text/plain",
                        key=f"sum_{record['id']}"
                    )
                
                with col_c:
                    analysis_json = json.dumps(record, indent=2)
                    st.download_button(
                        label="📥 Full JSON",
                        data=analysis_json,
                        file_name=f"analysis_{record['client_name']}_{record['call_date']}.json",
                        mime="application/json",
                        key=f"json_{record['id']}"
                    )

# Admin View Page
elif page == "Admin View":
    st.title("👨‍💼 Admin Dashboard")
    
    db = load_db()
    
    if not db:
        st.info("No data available yet.")
    else:
        st.subheader("📈 Overall Statistics")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Calls", len(db))
        with col2:
            success_count = len([r for r in db if "Success" in r['pitch_outcome']])
            st.metric("Successful", success_count)
        with col3:
            avg_score = sum([r['analysis'].get('overall_score', 0) for r in db]) / len(db)
            st.metric("Avg Score", f"{avg_score:.1f}/100")
        with col4:
            avg_compliance = sum([r['analysis'].get('methodology_compliance', 0) for r in db]) / len(db)
            st.metric("Avg IL Compliance", f"{avg_compliance:.1f}%")
        with col5:
            unique_rms = len(set([r['rm_name'] for r in db]))
            st.metric("Active RMs", unique_rms)
        
        # Bulk operations
        st.markdown("---")
        st.subheader("⚠️ Bulk Operations")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Delete All Records"):
                if st.checkbox("Confirm deletion"):
                    save_db([])
                    st.success("All deleted!")
                    st.rerun()
        
        with col2:
            all_data = json.dumps(db, indent=2)
            st.download_button(
                label="📥 Backup All (JSON)",
                data=all_data,
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
            selected_call_type = st.selectbox("Filter by Call Type", ["All"] + list(CALL_TYPE_FOCUS.keys()))
        with col3:
            selected_outcome = st.selectbox("Filter by Outcome", ["All", "Success - Committed", "Partial - Needs Follow-up", "Not Interested", "Rescheduled"])
        with col4:
            score_filter = st.selectbox("Score Range", ["All", "90-100", "75-89", "60-74", "Below 60"])
        
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
                filtered_db = [r for r in filtered_db if r['analysis'].get('overall_score', 0) >= 90]
            elif "75-89" in score_filter:
                filtered_db = [r for r in filtered_db if 75 <= r['analysis'].get('overall_score', 0) < 90]
            elif "60-74" in score_filter:
                filtered_db = [r for r in filtered_db if 60 <= r['analysis'].get('overall_score', 0) < 75]
            elif "Below 60" in score_filter:
                filtered_db = [r for r in filtered_db if r['analysis'].get('overall_score', 0) < 60]
        
        st.markdown("---")
        st.subheader(f"📊 Results ({len(filtered_db)} calls)")
        
        # DataFrame
        df_data = []
        for record in filtered_db:
            df_data.append({
                "ID": record['id'],
                "Date": record['call_date'],
                "RM": record['rm_name'],
                "Participant": record['client_name'],
                "Call Type": record.get('call_type', 'N/A'),
                "Score": f"{record['analysis'].get('overall_score', 0):.1f}",
                "IL %": f"{record['analysis'].get('methodology_compliance', 0):.1f}%",
                "Storage": record.get('storage_type', 'local')
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
            # Detailed records
            st.markdown("---")
            st.subheader("🔍 Detailed Records")
            
            for record in reversed(filtered_db[:20]):
                analysis = record.get('analysis', {})
                with st.expander(f"{record['rm_name']} - {record['call_type']} - {record['client_name']} ({record['call_date']})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**ID:** {record['id']}")
                        st.write(f"**RM:** {record['rm_name']}")
                        st.write(f"**Participant:** {record['client_name']}")
                        st.write(f"**Storage:** {record.get('storage_type', 'local')}")
                    
                    with col2:
                        st.write(f"**Score:** {analysis.get('overall_score', 0):.1f}/100")
                        st.write(f"**IL Compliance:** {analysis.get('methodology_compliance', 0):.1f}%")
                        st.write(f"**Effectiveness:** {analysis.get('call_effectiveness', 'N/A')}")
                    
                    st.write(f"**Summary:** {analysis.get('call_summary', 'N/A')}")
                    
                    # Action buttons
                    col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])
                    with col_a:
                        if st.button("🗑️ Delete", key=f"del_admin_{record['id']}"):
                            delete_record(record['id'])
                            st.success("Deleted!")
                            st.rerun()
                    
                    with col_b:
                        summary = generate_summary_report(record)
                        st.download_button(
                            label="📄 Summary",
                            data=summary,
                            file_name=f"summary_{record['id']}.txt",
                            mime="text/plain",
                            key=f"sum_adm_{record['id']}"
                        )
                    
                    with col_c:
                        json_data = json.dumps(record, indent=2)
                        st.download_button(
                            label="📥 JSON",
                            data=json_data,
                            file_name=f"record_{record['id']}.json",
                            mime="application/json",
                            key=f"json_adm_{record['id']}"
                        )

# Footer
st.sidebar.markdown("---")
st.sidebar.info("💡 Use GPT for AI analysis or Manual for precise control!")
st.sidebar.markdown("**Iron Lady Framework**")
st.sidebar.markdown("• 27 Principles")
st.sidebar.markdown("• BHAG Focus")
st.sidebar.markdown("• Community Power")
st.sidebar.markdown("---")
st.sidebar.markdown("Built for Iron Lady 👩‍💼")
