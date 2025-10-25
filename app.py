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

def upload_analysis_to_s3(record):
    """Upload analysis JSON to S3 (auto-deletes after 7 days via lifecycle policy)"""
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()
    
    if not s3_client or not bucket_name:
        return None
    
    try:
        date_path = datetime.now().strftime("%Y/%m/%d")
        # Store under 'recordings/' prefix so same lifecycle policy applies
        analysis_key = f"recordings/analysis/{date_path}/analysis_{record['id']}_{record['rm_name'].replace(' ', '_')}_{record['call_date']}.json"
        
        analysis_json = json.dumps(record, indent=2)
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=analysis_key,
            Body=analysis_json.encode('utf-8'),
            ContentType='application/json',
            ServerSideEncryption='AES256',
            Metadata={
                'rm_name': record['rm_name'],
                'client_name': record['client_name'],
                'call_type': record.get('call_type', ''),
                'overall_score': str(record['analysis'].get('overall_score', 0)),
                'record_id': str(record['id'])
            }
        )
        
        return f"s3://{bucket_name}/{analysis_key}"
    except Exception as e:
        st.error(f"Failed to upload analysis to S3: {str(e)}")
        return None

def generate_summary_report(record):
    """Generate downloadable summary with improvements and areas needing focus"""
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
💎 IRON LADY SPECIFIC PARAMETERS (Sorted by Performance)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # Sort parameters by score for better visibility
    il_params = analysis.get('iron_lady_parameters', {})
    sorted_params = sorted(il_params.items(), key=lambda x: x[1], reverse=True)
    
    for param, score in sorted_params:
        pct = (score / 10) * 100
        if pct >= 80:
            status = "🟢 Excellent"
        elif pct >= 60:
            status = "🟡 Good    "
        else:
            status = "🔴 Needs Focus"
        report += f"{status}  {param.replace('_', ' ').title():<25} {score:>2}/10 ({pct:>3.0f}%)\n"
    
    report += f"""
📊 PERFORMANCE BREAKDOWN BY CATEGORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 EXCELLENT (80%+):
"""
    excellent = [f"   • {p.replace('_', ' ').title()} - {s}/10 ({(s/10*100):.0f}%)" 
                 for p, s in sorted_params if (s/10*100) >= 80]
    if excellent:
        report += "\n".join(excellent) + "\n"
    else:
        report += "   (None - Focus on building excellence in key areas)\n"
    
    report += f"""
🟡 GOOD (60-79%):
"""
    good = [f"   • {p.replace('_', ' ').title()} - {s}/10 ({(s/10*100):.0f}%)" 
            for p, s in sorted_params if 60 <= (s/10*100) < 80]
    if good:
        report += "\n".join(good) + "\n"
    else:
        report += "   (None)\n"
    
    report += f"""
🔴 NEEDS IMMEDIATE FOCUS (<60%):
"""
    needs_focus = [f"   • {p.replace('_', ' ').title()} - {s}/10 ({(s/10*100):.0f}%) ⚠️ PRIORITY" 
                   for p, s in sorted_params if (s/10*100) < 60]
    if needs_focus:
        report += "\n".join(needs_focus) + "\n"
    else:
        report += "   (None - Great job!)\n"
    
    report += f"""
✅ KEY STRENGTHS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for i, s in enumerate(analysis.get('key_insights', {}).get('strengths', []), 1):
        report += f"{i}. {s}\n"
    
    report += f"""
🔴 CRITICAL IMPROVEMENT AREAS (TOP PRIORITY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for i, g in enumerate(analysis.get('key_insights', {}).get('critical_gaps', []), 1):
        report += f"{i}. ⚠️  {g}\n"
    
    report += f"""
⚠️ MISSED OPPORTUNITIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for i, o in enumerate(analysis.get('key_insights', {}).get('missed_opportunities', []), 1):
        report += f"{i}. {o}\n"
    
    report += f"""
💡 GENERAL COACHING RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for i, r in enumerate(analysis.get('coaching_recommendations', []), 1):
        report += f"{i}. {r}\n"
    
    report += f"""
🎓 IRON LADY SPECIFIC COACHING (METHODOLOGY FOCUS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for i, r in enumerate(analysis.get('iron_lady_specific_coaching', []), 1):
        report += f"{i}. 💎 {r}\n"
    
    report += f"""
🎯 ACTION PLAN - NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    # Generate action plan based on weakest areas
    action_items = []
    for param, score in sorted_params[-3:]:  # Bottom 3 parameters
        if score < 7:
            param_name = param.replace('_', ' ').title()
            if 'principles' in param:
                action_items.append(f"• PRACTICE: Memorize and use 27 Principles by name in every call")
            elif 'case_studies' in param:
                action_items.append(f"• PRACTICE: Learn all 6 case studies (Neha, Rashmi, Chandana, etc.) and use specific names")
            elif 'commitment' in param:
                action_items.append(f"• PRACTICE: Always ask for explicit commitments (Day 2, Day 3, follow-up calls)")
            elif 'bhag' in param:
                action_items.append(f"• PRACTICE: Spend 5+ minutes on BHAG, help participants dream 2-3x bigger")
            else:
                action_items.append(f"• IMPROVE: Focus on {param_name} - aim for 8+/10")
    
    if action_items:
        report += "\n".join(action_items[:5]) + "\n"
    else:
        report += "• Continue maintaining excellent performance across all parameters\n"
    
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
Iron Lady Call Analysis System
All S3 Storage: Auto-deletes after 7 days (Recordings + Analysis JSON)
═══════════════════════════════════════════════════════════════════
"""
    return report

# Create data directory (database only, not uploads)
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DB_FILE = DATA_DIR / "calls_database.json"

# Iron Lady Parameters
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

# Iron Lady Company Context for GPT Training
IRON_LADY_CONTEXT = """
**IRON LADY PROGRAM OVERVIEW:**
Iron Lady is a transformational leadership and business growth program for women entrepreneurs and professionals. The program focuses on helping participants achieve their BHAG (Big Hairy Audacious Goal) through proven frameworks and community support.

**PROGRAM STRUCTURE:**
- 3-Day Intensive Program: Day 1 & 2 (Workshop), Day 3 (Follow-up session)
- Certification upon completion
- Ongoing community support and networking
- Access to mentors and successful Iron Lady alumni
- Focus on personal branding and business scaling

**27 CORE PRINCIPLES (Must be mentioned by name in calls):**
1. Unpredictable Behaviour - Stand out from competition
2. 10,000 Hours Rule - Mastery through dedicated practice
3. Differentiate Branding - Create unique positioning
4. Maximize - Optimize all resources and opportunities
5. Shameless Pitching - Confident selling without hesitation
6. Art of Negotiation - Win-win deal making
7. Contextualisation - Personalize approach to each situation
(And 20 more principles covered in the program)

**SUCCESS CASE STUDIES (Must use specific names):**
- Neha: Rose to Big 4 Partner position, multiplied income 5x
- Rashmi: Senior Leader who transformed her career trajectory
- Chandana: Entrepreneur who scaled her business significantly
- Annapurna: Built thriving consulting practice
- Pushpalatha: Achieved breakthrough in corporate leadership
- Tejaswini: Successfully pivoted to entrepreneurship

**PROGRAM BENEFITS:**
- Community of ambitious women entrepreneurs
- Proven frameworks for business growth
- Personal brand development
- Confidence building and mindset transformation
- Pricing strategies for premium positioning
- Network of successful women leaders
- Accountability and ongoing support

**IDEAL CALL ELEMENTS:**
1. Warm, empathetic greeting using participant's name multiple times
2. Strategic questions to understand BHAG and current situation
3. Mention specific 27 Principles by name (e.g., "Differentiate Branding", "Shameless Pitching")
4. Share specific case studies with actual names (Neha, Rashmi, etc.)
5. Create gap between current state and BHAG
6. Encourage dreaming bigger (expand their BHAG)
7. Create urgency (limited cohort spots, immediate action needed)
8. Get explicit commitments (attend Day 2, Day 3, take follow-up call)
9. Use "Powerfully Invite" language in closing
10. Personalize everything to their specific situation

**KEY METRICS FOR EXCELLENCE:**
- Use participant's name 5+ times in call
- Ask 8+ strategic questions about their business/goals
- Mention at least 2-3 principles by exact name
- Reference at least 2 specific case studies with names
- Explicitly state what's missing to achieve their BHAG
- Encourage them to think 2-3x bigger than current BHAG
- Create clear urgency and FOMO
- Secure minimum 2 explicit commitments
- Close with "Powerfully invite you to..." language
"""

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
    """Delete a record from the database and optionally offer to re-analyze"""
    db = load_db()
    db = [r for r in db if r['id'] != record_id]
    save_db(db)
    return True

def check_for_duplicate_analysis(rm_name, client_name, call_date):
    """Check if analysis already exists for same RM, participant, and date"""
    db = load_db()
    for record in db:
        if (record.get('rm_name') == rm_name and 
            record.get('client_name') == client_name and 
            record.get('call_date') == str(call_date)):
            return record
    return None

def analyze_call_with_gpt(call_type, additional_context, manual_scores=None):
    """Hybrid analysis: GPT or manual scores with Iron Lady context"""
    try:
        if manual_scores:
            return generate_analysis_from_scores(manual_scores, call_type, "Manual scoring with GPT-generated insights")
        
        focus_areas = CALL_TYPE_FOCUS.get(call_type, [])
        
        prompt = f"""{IRON_LADY_CONTEXT}

**YOUR TASK:**
Analyze this {call_type} call based on the Iron Lady methodology described above and the actual call content below.

**CALL CONTENT:**
{additional_context}

**STRICT SCORING RULES:**

**Rapport Building (0-20):**
- 0-5: Cold, no name usage, transactional
- 6-10: Basic greeting, name used 1-2 times
- 11-15: Warm, name used 3-4 times, some empathy
- 16-20: Exceptional warmth, name used 5+ times, high empathy, strong connection

**Needs Discovery (0-25):**
- 0-6: 0-2 questions asked
- 7-12: 3-5 basic questions
- 13-18: 6-7 strategic questions
- 19-25: 8+ strategic questions with deep BHAG exploration

**Solution Presentation (0-25):**
- 0-6: Program barely mentioned
- 7-12: Basic program description
- 13-18: Good explanation with 3-4 benefits
- 19-25: Comprehensive presentation with program structure, community, outcomes, social proof

**Objection Handling (0-15):**
- 0-3: Concerns dismissed or ignored
- 4-7: Basic acknowledgment
- 8-11: Good handling with empathy
- 12-15: Excellent handling with empathy, solutions, and case studies

**Closing Technique (0-15):**
- 0-3: No close or very weak
- 4-7: Vague next steps
- 8-11: Clear next steps
- 12-15: "Powerfully invite" language used, explicit commitments secured

**Iron Lady Parameters (each 0-10):**

**Profile Understanding:** Did they deeply understand background, experience, current challenges, and goals?
**Credibility Building:** Did they mention Iron Lady community, success stories, certification, mentors?
**Principles Usage:** How many of the 27 Principles were mentioned BY NAME? (0 names = max 3 points)
**Case Studies Usage:** Did they share specific participant names? (No names = max 4 points)
**Gap Creation:** Did they clearly articulate what's missing between current state and BHAG?
**BHAG Fine Tuning:** Did they help participant dream bigger and expand their BHAG?
**Urgency Creation:** Did they create FOMO, mention limited spots, immediate action needed?
**Commitment Getting:** Did they get explicit commitments? (No commitments = max 4 points)
**Contextualisation:** How well was everything personalized to participant's specific situation?
**Excitement Creation:** Did they generate genuine enthusiasm about the transformation journey?

**CRITICAL PENALTIES:**
- NO principles mentioned by name = Principles Usage max 3/10
- NO case study names mentioned = Case Studies Usage max 4/10
- NO BHAG exploration = BHAG Fine Tuning max 4/10
- NO explicit commitments = Commitment Getting max 4/10

Respond ONLY with this JSON format:

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
    "justification": "Brief explanation of scores based on actual call performance"
}}
"""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert Iron Lady sales call analyst trained on the Iron Lady methodology. Score calls strictly based on adherence to the 27 Principles framework, BHAG exploration, case study usage, and commitment getting. Be realistic and strict - most calls will score 50-70/100. Only exceptional calls following all guidelines score 80+."},
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
            scores_data.get('justification', 'GPT analysis based on Iron Lady methodology'),
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
        strengths = ["Professional approach maintained"]
    if not critical_gaps:
        critical_gaps = ["Fine-tune methodology execution"]
    if not missed_opportunities:
        missed_opportunities = ["Deepen Iron Lady framework usage"]
    if not best_moments:
        best_moments = ["Call structure followed"]
    
    coaching_recommendations = []
    il_coaching = []
    
    sorted_core = sorted(core_dimensions.items(), key=lambda x: x[1])
    sorted_il = sorted(iron_lady_parameters.items(), key=lambda x: x[1])
    
    for param, score in sorted_core[:3]:
        max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][param]["weight"]
        if score < max_score * 0.7:
            coaching_recommendations.append(f"Priority: Improve {param.replace('_', ' ').title()} to {int(max_score*0.8)}/{max_score}")
    
    for param, score in sorted_il[:4]:
        if score < 7:
            il_coaching.append(f"Focus: {param.replace('_', ' ').title()} needs work (current: {score}/10, target: 8+)")
    
    # Add Iron Lady specific coaching
    if iron_lady_parameters.get('principles_usage', 0) < 7:
        il_coaching.insert(0, "CRITICAL: Mention 27 Principles by name (e.g., 'Differentiate Branding', 'Shameless Pitching')")
    if iron_lady_parameters.get('case_studies_usage', 0) < 7:
        il_coaching.insert(0, "CRITICAL: Use specific case study names (Neha, Rashmi, Chandana, etc.)")
    if iron_lady_parameters.get('commitment_getting', 0) < 7:
        il_coaching.insert(0, "CRITICAL: Get explicit commitments (Day 2 attendance, Day 3, follow-up call)")
    
    if not coaching_recommendations:
        coaching_recommendations = ["Maintain current performance levels", "Continue professional approach"]
    if not il_coaching:
        il_coaching = ["Integrate more 27 Principles by name", "Use more case studies", "Deepen BHAG exploration"]
    
    commit_score = iron_lady_parameters.get('commitment_getting', 0)
    bhag_score = iron_lady_parameters.get('bhag_fine_tuning', 0)
    
    if overall_score >= 80 and commit_score >= 7 and bhag_score >= 7:
        likely_result = "registration_expected"
        confidence = min(95, int(overall_score + 5))
        reasoning = f"Strong Iron Lady methodology execution ({overall_score:.0f}/100) with solid commitments"
    elif overall_score >= 60:
        likely_result = "follow_up_needed"
        confidence = min(80, int(overall_score - 5))
        reasoning = f"Moderate performance ({overall_score:.0f}/100), follow-up required"
    else:
        likely_result = "needs_improvement"
        confidence = min(70, int(overall_score - 15))
        reasoning = f"Below Iron Lady standards ({overall_score:.0f}/100), coaching needed"
    
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
st.sidebar.markdown("**AI-Powered Analysis**")
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
    else:
        st.sidebar.warning("S3 stats unavailable")
except:
    st.sidebar.error("⚠️ S3 not configured")
    st.sidebar.caption("Add AWS credentials to secrets")

page = st.sidebar.radio("Navigate", ["Upload & Analyze", "Dashboard", "Admin View", "Parameters Guide"])

# Parameters Guide Page
if page == "Parameters Guide":
    st.title("📚 Iron Lady Parameters Guide")
    st.markdown("Complete breakdown of all parameters and Iron Lady methodology")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Core Dimensions", "Iron Lady Parameters", "Call Type Focus", "27 Principles & Case Studies"])
    
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
    
    with tab4:
        st.subheader("🎓 Iron Lady Methodology")
        
        st.markdown("### 27 Principles (Must mention by name)")
        st.write("**Key Principles to Reference:**")
        st.write("• Unpredictable Behaviour - Stand out from competition")
        st.write("• 10,000 Hours Rule - Mastery through practice")
        st.write("• Differentiate Branding - Unique positioning")
        st.write("• Shameless Pitching - Confident selling")
        st.write("• Art of Negotiation - Win-win deals")
        st.write("• Contextualisation - Personalize approach")
        st.write("• Maximize - Optimize resources")
        
        st.markdown("---")
        st.markdown("### Success Case Studies (Use specific names)")
        st.write("**Featured Participants:**")
        st.write("• **Neha** - Rose to Big 4 Partner, 5x income growth")
        st.write("• **Rashmi** - Senior Leader transformation")
        st.write("• **Chandana** - Entrepreneur who scaled significantly")
        st.write("• **Annapurna** - Built thriving consulting practice")
        st.write("• **Pushpalatha** - Corporate leadership breakthrough")
        st.write("• **Tejaswini** - Successful entrepreneurship pivot")
        
        st.markdown("---")
        st.markdown("### Program Structure")
        st.write("• 3-Day Intensive: Day 1 & 2 (Workshop), Day 3 (Follow-up)")
        st.write("• Certification upon completion")
        st.write("• Community of successful women entrepreneurs")
        st.write("• Access to mentors and alumni network")
        st.write("• Personal branding and business scaling focus")

# Upload Page
elif page == "Upload & Analyze":
    st.title("📤 Upload Call & Get AI Analysis")
    st.write("AI trained on Iron Lady methodology will analyze your call")
    
    # GPT-only analysis (v3.0 - manual scoring removed)
    analysis_mode = "GPT Auto-Analysis"  # Fixed to GPT-only
    
    with st.form("upload_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            rm_name = st.text_input("RM Name *", placeholder="e.g., Priya Sharma")
            client_name = st.text_input("Participant Name *", placeholder="e.g., Anjali Mehta")
            call_type = st.selectbox("Call Type *", list(CALL_TYPE_FOCUS.keys()))
        
        with col2:
            pitch_outcome = st.selectbox("Call Outcome *", ["Success - Committed", "Partial - Needs Follow-up", "Not Interested", "Rescheduled"])
            call_date = st.date_input("Call Date *", datetime.now())
            call_duration = st.number_input("Call Duration (minutes)", 1, 120, 15)
        
        uploaded_file = st.file_uploader("Upload Recording *", type=['mp3', 'wav', 'm4a', 'mp4'], help="Max 40MB")
        
        st.markdown(f"### 📋 Key Focus for {call_type}")
        focus_params = CALL_TYPE_FOCUS.get(call_type, [])
        st.info("✓ " + " • ".join([p.replace('_', ' ').title() for p in focus_params[:5]]))
        
        if "GPT" in analysis_mode:
            st.markdown("### 📝 Call Summary (AI will analyze this)")
            
            # Pre-filled template
            template = f"""**Participant Profile & BHAG:**
- Current Role/Business: [e.g., Running yoga classes, 15 students, ₹30k/month]
- BHAG (Big Goal): [e.g., Launch ₹50 lakh/year coaching practice in 12 months]
- Main Challenges: [e.g., Pricing, confidence, scaling]

**Questions Asked (List all):**
1. [e.g., What's your biggest challenge in scaling?]
2. [e.g., What would your ideal business look like in 2 years?]
3. [Add all questions...]

**27 Principles Mentioned (Use exact names):**
- [e.g., "Differentiate Branding" - Discussed personal brand positioning]
- [e.g., "Shameless Pitching" - Talked about confident selling]
- [List all principles mentioned BY NAME]

**Case Studies Shared (Use actual participant names):**
- [e.g., Neha's story - Big 4 Partner success]
- [e.g., Rashmi's transformation as Senior Leader]
- [List all with specific names]

**BHAG Exploration:**
- How deeply was BHAG explored? [e.g., Spent 5 minutes discussing, helped expand from ₹50L to ₹1Cr target]
- Did you help them dream bigger? [Yes/No and how]

**Gap Creation:**
- What gaps were highlighted? [e.g., Missing: network, premium pricing skills, confidence]
- How was the gap between current state and BHAG articulated?

**Urgency & Commitments:**
- Urgency created? [e.g., Limited 20 spots in cohort, closes Friday]
- Explicit commitments obtained: [e.g., "Yes, I'll attend Day 2 and Day 3", "I'll take the follow-up call on Tuesday"]

**Objections & Handling:**
- Concerns raised: [e.g., Time management, investment]
- How handled: [e.g., Shared time-saving strategies, ROI examples]

**Closing:**
- Did you use "Powerfully invite" language? [e.g., "I powerfully invite you to join this transformational journey"]
- Clear next steps? [e.g., Day 2 on Saturday 10 AM, follow-up call Monday]

**Rapport & Tone:**
- Participant name used how many times? [Count]
- Overall warmth and empathy level? [High/Medium/Low]
- Best moments of connection? [List]
"""
            
            additional_context = st.text_area(
                "Call Summary & Details *",
                value=template,
                placeholder="Fill in the template above with actual call details...",
                height=400,
                help="Be specific! AI analyzes based on what you write here."
            )
            
            st.info("💡 **Tip:** The more detailed your summary, the more accurate the AI analysis. Mention specific principle names and case study names!")
            
        # Manual scoring removed in v3.0 - GPT-only analysis
        
        notes = st.text_area("Additional Notes (Optional)", placeholder="Any other observations...")
        submitted = st.form_submit_button("🚀 Analyze Call", use_container_width=True)
    
    if submitted:
        if not all([rm_name, client_name, uploaded_file]):
            st.error("❌ Please fill all required fields (*)")
        elif len(additional_context.strip()) < 200:
            st.error("❌ Please provide detailed call summary (minimum 200 characters). AI needs details to analyze accurately!")
        else:
            # Check for duplicate analysis
            existing_record = check_for_duplicate_analysis(rm_name, client_name, call_date)
            
            if existing_record:
                st.warning(f"⚠️ An analysis already exists for {client_name} by {rm_name} on {call_date}")
                st.write(f"**Existing Score:** {existing_record['analysis'].get('overall_score', 0):.1f}/100")
                st.write(f"**Call Type:** {existing_record.get('call_type', 'N/A')}")
                
                replace_option = st.radio(
                    "What would you like to do?",
                    ["Cancel upload", "Replace existing analysis with new one"],
                    key="replace_decision"
                )
                
                if replace_option == "Cancel upload":
                    st.info("Upload cancelled. No changes made.")
                    st.stop()
                else:
                    st.info("✅ Proceeding to replace existing analysis...")
                    # Delete the old record
                    delete_record(existing_record['id'])
            
            with st.spinner(f"🔄 Uploading to S3 and analyzing with AI..."):
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
                    st.error("❌ S3 upload failed. Check AWS configuration.")
                    st.stop()
                
                st.success(f"✅ File uploaded to S3 (auto-deletes in 7 days)")
                
                # Analyze
                # Analyze - Pure GPT only (v3.0)
                analysis = analyze_call_with_gpt(call_type, additional_context)
                
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
                    "analysis_mode": "GPT Auto-Analysis (v3.0)",
                    "analysis": analysis
                }
                db.append(record)
                save_db(db)
                
                # Upload analysis to S3
                analysis_s3_url = upload_analysis_to_s3(record)
                if analysis_s3_url:
                    st.success(f"✅ Analysis JSON backed up to S3 (auto-deletes in 7 days)")
                
                st.success("✅ Analysis Complete!")
                
                # Display results
                st.markdown("---")
                st.subheader(f"📊 Analysis Results - {call_type}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    score_color = "🟢" if analysis['overall_score'] >= 80 else "🟡" if analysis['overall_score'] >= 60 else "🔴"
                    st.metric("Overall Score", f"{score_color} {analysis['overall_score']:.1f}/100")
                with col2:
                    st.metric("IL Compliance", f"{analysis['methodology_compliance']:.1f}%")
                with col3:
                    st.metric("Effectiveness", analysis['call_effectiveness'])
                with col4:
                    pred_emoji = {"registration_expected": "🎉", "follow_up_needed": "📞", "needs_improvement": "⚠️"}
                    pred_result = analysis['outcome_prediction']['likely_result']
                    st.metric("Prediction", f"{pred_emoji.get(pred_result, '📊')} {pred_result.replace('_', ' ').title()}")
                
                st.markdown("**Executive Summary:**")
                st.info(analysis['call_summary'])
                
                # Core Dimensions
                st.markdown("### 🎯 Core Dimensions")
                core_df = pd.DataFrame([
                    {
                        "Dimension": k.replace('_', ' ').title(), 
                        "Score": v, 
                        "Max": IRON_LADY_PARAMETERS["Core Quality Dimensions"][k]["weight"],
                        "%": f"{(v/IRON_LADY_PARAMETERS['Core Quality Dimensions'][k]['weight']*100):.0f}%",
                        "Status": "🟢" if (v/IRON_LADY_PARAMETERS['Core Quality Dimensions'][k]['weight']*100) >= 80 else "🟡" if (v/IRON_LADY_PARAMETERS['Core Quality Dimensions'][k]['weight']*100) >= 60 else "🔴"
                    }
                    for k, v in analysis['core_dimensions'].items()
                ])
                st.dataframe(core_df, use_container_width=True, hide_index=True)
                
                # IL Parameters
                st.markdown("### 💎 Iron Lady Parameters")
                il_df = pd.DataFrame([
                    {
                        "Parameter": k.replace('_', ' ').title(), 
                        "Score": v, 
                        "Max": 10,
                        "%": f"{(v/10*100):.0f}%",
                        "Status": "🟢" if (v/10*100) >= 80 else "🟡" if (v/10*100) >= 60 else "🔴"
                    }
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
                
                st.markdown("### 💡 General Coaching Recommendations")
                for i, rec in enumerate(analysis['coaching_recommendations'], 1):
                    st.write(f"{i}. {rec}")
                
                st.markdown("### 🎓 Iron Lady Specific Coaching")
                for i, rec in enumerate(analysis['iron_lady_specific_coaching'], 1):
                    st.write(f"{i}. 💎 {rec}")
                
                # Outcome Prediction
                st.markdown("### 🔮 Outcome Prediction")
                pred = analysis['outcome_prediction']
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Likely Result", pred['likely_result'].replace('_', ' ').title())
                    st.metric("Confidence", f"{pred['confidence']}%")
                with col2:
                    st.write(f"**Reasoning:**")
                    st.write(pred['reasoning'])

# Dashboard Page
elif page == "Dashboard":
    st.title("📊 My Dashboard")
    
    rm_filter = st.text_input("Filter by your name", placeholder="Enter your name")
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
            score = analysis.get('overall_score', 0)
            score_emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
            
            with st.expander(
                f"{score_emoji} {record['call_type']} - {record['client_name']} - {record['call_date']} "
                f"(Score: {score:.1f}/100)"
            ):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**RM:** {record['rm_name']}")
                    st.write(f"**Participant:** {record['client_name']}")
                    st.write(f"**Call Type:** {record['call_type']}")
                    st.write(f"**Outcome:** {record['pitch_outcome']}")
                    st.write(f"**Duration:** {record.get('call_duration', 'N/A')} min")
                    st.write(f"**Storage:** {record.get('storage_type', 'local')} (7-day auto-delete)")
                    st.write(f"**Analysis JSON:** S3 (7-day auto-delete)")
                    st.write(f"**Summary:** {analysis.get('call_summary', 'N/A')}")
                
                with col2:
                    st.metric("Score", f"{score:.1f}/100")
                    st.metric("IL Compliance", f"{analysis.get('methodology_compliance', 0):.1f}%")
                    st.write(f"**Effectiveness:**")
                    st.write(analysis.get('call_effectiveness', 'N/A'))
                
                st.markdown("**Top 3 Strengths:**")
                for s in analysis.get('key_insights', {}).get('strengths', [])[:3]:
                    st.write(f"✓ {s}")
                
                st.markdown("**Top 3 Gaps:**")
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
                        file_name=f"Iron_Lady_Summary_{record['rm_name']}_{record['call_date']}.txt",
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
        
        # Call Type Performance
        st.markdown("---")
        st.subheader("📊 Performance by Call Type")
        call_type_stats = {}
        for r in db:
            ct = r.get('call_type', 'Unknown')
            if ct not in call_type_stats:
                call_type_stats[ct] = {'count': 0, 'scores': []}
            call_type_stats[ct]['count'] += 1
            call_type_stats[ct]['scores'].append(r['analysis'].get('overall_score', 0))
        
        ct_df = pd.DataFrame([
            {
                'Call Type': ct,
                'Count': data['count'],
                'Avg Score': f"{sum(data['scores'])/len(data['scores']):.1f}",
                'Success Rate': f"{(len([s for s in data['scores'] if s >= 70])/len(data['scores'])*100):.0f}%"
            }
            for ct, data in call_type_stats.items()
        ])
        st.dataframe(ct_df, use_container_width=True, hide_index=True)
        
        # Bulk operations
        st.markdown("---")
        st.subheader("⚠️ Bulk Operations")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Delete All Records (Careful!)"):
                if st.checkbox("✅ I confirm deletion of ALL records"):
                    save_db([])
                    st.success("All records deleted!")
                    st.rerun()
        
        with col2:
            all_data = json.dumps(db, indent=2)
            st.download_button(
                label="📥 Backup All Data (JSON)",
                data=all_data,
                file_name=f"iron_lady_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        # Filters
        st.markdown("---")
        st.subheader("🔍 Advanced Filters")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            rm_list = ["All"] + sorted(list(set([r['rm_name'] for r in db])))
            selected_rm = st.selectbox("Filter by RM", rm_list)
        with col2:
            selected_call_type = st.selectbox("Filter by Call Type", ["All"] + list(CALL_TYPE_FOCUS.keys()))
        with col3:
            selected_outcome = st.selectbox("Filter by Outcome", ["All", "Success - Committed", "Partial - Needs Follow-up", "Not Interested", "Rescheduled"])
        with col4:
            score_filter = st.selectbox("Score Range", ["All", "Excellent (85-100)", "Good (70-84)", "Average (50-69)", "Needs Work (<50)"])
        
        # Apply filters
        filtered_db = db
        if selected_rm != "All":
            filtered_db = [r for r in filtered_db if r['rm_name'] == selected_rm]
        if selected_call_type != "All":
            filtered_db = [r for r in filtered_db if r.get('call_type') == selected_call_type]
        if selected_outcome != "All":
            filtered_db = [r for r in filtered_db if r['pitch_outcome'] == selected_outcome]
        if score_filter != "All":
            if "Excellent" in score_filter:
                filtered_db = [r for r in filtered_db if r['analysis'].get('overall_score', 0) >= 85]
            elif "Good" in score_filter:
                filtered_db = [r for r in filtered_db if 70 <= r['analysis'].get('overall_score', 0) < 85]
            elif "Average" in score_filter:
                filtered_db = [r for r in filtered_db if 50 <= r['analysis'].get('overall_score', 0) < 70]
            elif "Needs Work" in score_filter:
                filtered_db = [r for r in filtered_db if r['analysis'].get('overall_score', 0) < 50]
        
        st.markdown("---")
        st.subheader(f"📊 Filtered Results ({len(filtered_db)} calls)")
        
        # DataFrame
        df_data = []
        for record in filtered_db:
            score = record['analysis'].get('overall_score', 0)
            status = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
            df_data.append({
                "Status": status,
                "ID": record['id'],
                "Date": record['call_date'],
                "RM": record['rm_name'],
                "Participant": record['client_name'],
                "Call Type": record.get('call_type', 'N/A'),
                "Score": f"{score:.1f}",
                "IL %": f"{record['analysis'].get('methodology_compliance', 0):.1f}%",
                "Outcome": record['pitch_outcome']
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Generate comprehensive CSV export
            comprehensive_data = []
            for record in filtered_db:
                analysis = record.get('analysis', {})
                core_dims = analysis.get('core_dimensions', {})
                il_params = analysis.get('iron_lady_parameters', {})
                
                # Base record info
                row = {
                    "ID": record['id'],
                    "Date": record['call_date'],
                    "RM Name": record['rm_name'],
                    "Participant": record['client_name'],
                    "Call Type": record.get('call_type', 'N/A'),
                    "Duration (min)": record.get('call_duration', 'N/A'),
                    "Outcome": record['pitch_outcome'],
                    "Overall Score": f"{analysis.get('overall_score', 0):.1f}",
                    "IL Compliance %": f"{analysis.get('methodology_compliance', 0):.1f}",
                    "Effectiveness": analysis.get('call_effectiveness', 'N/A'),
                    "Prediction": analysis.get('outcome_prediction', {}).get('likely_result', 'N/A').replace('_', ' ').title(),
                    "Confidence %": analysis.get('outcome_prediction', {}).get('confidence', 0)
                }
                
                # Add core dimensions with percentages
                weights = {
                    "rapport_building": 20,
                    "needs_discovery": 25,
                    "solution_presentation": 25,
                    "objection_handling": 15,
                    "closing_technique": 15
                }
                for dim, score in core_dims.items():
                    max_score = weights.get(dim, 10)
                    pct = (score / max_score) * 100
                    row[f"CD: {dim.replace('_', ' ').title()}"] = f"{score}/{max_score}"
                    row[f"CD: {dim.replace('_', ' ').title()} %"] = f"{pct:.0f}%"
                
                # Add IL parameters with percentages and status
                sorted_il_params = sorted(il_params.items(), key=lambda x: x[1], reverse=True)
                for param, score in sorted_il_params:
                    pct = (score / 10) * 100
                    status = "Excellent" if pct >= 80 else "Good" if pct >= 60 else "Needs Focus"
                    row[f"IL: {param.replace('_', ' ').title()}"] = f"{score}/10"
                    row[f"IL: {param.replace('_', ' ').title()} %"] = f"{pct:.0f}%"
                    row[f"IL: {param.replace('_', ' ').title()} Status"] = status
                
                # Add areas needing improvement
                needs_improvement = []
                for param, score in sorted_il_params:
                    if (score / 10 * 100) < 60:
                        needs_improvement.append(param.replace('_', ' ').title())
                
                row["Areas Needing Improvement"] = "; ".join(needs_improvement) if needs_improvement else "None - All parameters good"
                
                # Add top 3 strengths
                strengths = analysis.get('key_insights', {}).get('strengths', [])
                row["Top Strengths"] = "; ".join(strengths[:3]) if strengths else "N/A"
                
                # Add top 3 gaps
                gaps = analysis.get('key_insights', {}).get('critical_gaps', [])
                row["Critical Gaps"] = "; ".join(gaps[:3]) if gaps else "N/A"
                
                # Add coaching recommendations
                coaching = analysis.get('iron_lady_specific_coaching', [])
                row["Coaching Focus"] = "; ".join(coaching[:3]) if coaching else "N/A"
                
                comprehensive_data.append(row)
            
            comprehensive_df = pd.DataFrame(comprehensive_data)
            csv = comprehensive_df.to_csv(index=False)
            
            st.download_button(
                label="📥 Download Comprehensive Report (CSV)",
                data=csv,
                file_name=f"iron_lady_comprehensive_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Includes all scores, parameters, percentages, and improvement areas"
            )
            
            # Parameter Performance Analysis
            st.markdown("---")
            st.subheader("📊 Iron Lady Parameter Performance")
            
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
                        "Avg Score": f"{score:.1f}/10",
                        "%": f"{(score/10*100):.0f}%",
                        "Status": "🟢 Excellent" if score >= 8 else "🟡 Good" if score >= 6 else "🔴 Needs Focus"
                    }
                    for param, score in sorted(param_avg.items(), key=lambda x: x[1], reverse=True)
                ])
                
                st.dataframe(param_df, use_container_width=True, hide_index=True)
                st.info("💡 **Team Coaching Focus:** Prioritize 🔴 parameters for immediate training and practice")
            
            # Detailed records
            st.markdown("---")
            st.subheader("🔍 Detailed Call Records")
            
            for record in reversed(filtered_db[:15]):  # Show last 15
                analysis = record.get('analysis', {})
                score = analysis.get('overall_score', 0)
                score_emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
                
                with st.expander(
                    f"{score_emoji} [{record['id']}] {record['rm_name']} - {record['call_type']} - "
                    f"{record['client_name']} ({record['call_date']}) - Score: {score:.1f}/100"
                ):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Call Information:**")
                        st.write(f"• Record ID: {record['id']}")
                        st.write(f"• RM: {record['rm_name']}")
                        st.write(f"• Participant: {record['client_name']}")
                        st.write(f"• Call Type: {record.get('call_type', 'N/A')}")
                        st.write(f"• Date: {record['call_date']}")
                        st.write(f"• Duration: {record.get('call_duration', 'N/A')} minutes")
                        st.write(f"• Outcome: {record['pitch_outcome']}")
                        st.write(f"• Storage: {record.get('storage_type', 'local')} (7-day auto-delete)")
                        st.write(f"• Analysis: S3 JSON (7-day auto-delete)")
                        st.write(f"• Analysis Mode: {record.get('analysis_mode', 'N/A')}")
                    
                    with col2:
                        st.write("**Performance Scores:**")
                        st.metric("Overall Score", f"{score:.1f}/100")
                        st.metric("IL Compliance", f"{analysis.get('methodology_compliance', 0):.1f}%")
                        st.metric("Effectiveness", analysis.get('call_effectiveness', 'N/A'))
                        pred = analysis.get('outcome_prediction', {})
                        st.write(f"**Prediction:** {pred.get('likely_result', 'N/A').replace('_', ' ').title()}")
                        st.write(f"**Confidence:** {pred.get('confidence', 0)}%")
                    
                    st.write(f"**Summary:** {analysis.get('call_summary', 'N/A')}")
                    
                    # Show parameter breakdown
                    if 'core_dimensions' in analysis:
                        st.markdown("**Core Dimensions:**")
                        for dim, score in analysis['core_dimensions'].items():
                            max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][dim]["weight"]
                            pct = (score / max_score) * 100
                            emoji = "🟢" if pct >= 80 else "🟡" if pct >= 60 else "🔴"
                            st.write(f"{emoji} {dim.replace('_', ' ').title()}: {score}/{max_score} ({pct:.0f}%)")
                    
                    if 'iron_lady_parameters' in analysis:
                        st.markdown("**Iron Lady Parameters:**")
                        for param, score in analysis['iron_lady_parameters'].items():
                            pct = (score / 10) * 100
                            emoji = "🟢" if pct >= 80 else "🟡" if pct >= 60 else "🔴"
                            st.write(f"{emoji} {param.replace('_', ' ').title()}: {score}/10 ({pct:.0f}%)")
                    
                    # Show top 3 strengths and gaps
                    insights = analysis.get('key_insights', {})
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        if insights.get('strengths'):
                            st.markdown("**Top Strengths:**")
                            for s in insights['strengths'][:3]:
                                st.write(f"✓ {s}")
                    
                    with col_b:
                        if insights.get('critical_gaps'):
                            st.markdown("**Critical Gaps:**")
                            for g in insights['critical_gaps'][:3]:
                                st.write(f"✗ {g}")
                    
                    # Coaching recommendations
                    if 'iron_lady_specific_coaching' in analysis:
                        st.markdown("**Iron Lady Coaching:**")
                        for i, rec in enumerate(analysis['iron_lady_specific_coaching'][:3], 1):
                            st.write(f"{i}. 💎 {rec}")
                    
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
                            label="📄 Report",
                            data=summary,
                            file_name=f"Iron_Lady_Report_{record['id']}.txt",
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
st.sidebar.info("💡 **Tip:** AI is trained on Iron Lady methodology. Mention principles by name and use case study names for accurate scoring!")
st.sidebar.markdown("**Iron Lady Methodology**")
st.sidebar.markdown("• 27 Principles Framework")
st.sidebar.markdown("• BHAG-Focused Approach")
st.sidebar.markdown("• Community Power")
st.sidebar.markdown("• Powerfully Invite Closing")
st.sidebar.markdown("• Case Study Leverage")
st.sidebar.markdown("---")
st.sidebar.markdown("Built for Iron Lady 👩‍💼")
st.sidebar.caption("AWS S3 Storage • 7-Day Auto-Delete")
st.sidebar.caption("(Recordings + Analysis JSON)")
