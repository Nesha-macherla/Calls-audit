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

def list_s3_recordings():
    """List all recordings in S3"""
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()
    
    if not s3_client or not bucket_name:
        return []
    
    try:
        recordings = []
        paginator = s3_client.get_paginator('list_objects_v2')
        
        # List audio recordings
        for page in paginator.paginate(Bucket=bucket_name, Prefix='recordings/'):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if not key.endswith('/') and '/analysis/' not in key:  # Skip folders and analysis JSONs
                        recordings.append({
                            'key': key,
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'filename': key.split('/')[-1]
                        })
        
        return recordings
    except Exception as e:
        st.error(f"Error listing S3 recordings: {str(e)}")
        return []

def list_s3_analyses():
    """List all analysis JSONs in S3 from recordings/analysis/YYYY/MM/ structure"""
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()
    
    if not s3_client or not bucket_name:
        return []
    
    try:
        analyses = []
        paginator = s3_client.get_paginator('list_objects_v2')
        
        # List analysis JSONs from recordings/analysis/
        for page in paginator.paginate(Bucket=bucket_name, Prefix='recordings/analysis/'):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith('.json'):  # Only JSON files
                        analyses.append({
                            'key': key,
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'filename': key.split('/')[-1]
                        })
        
        return sorted(analyses, key=lambda x: x['last_modified'], reverse=True)
    except Exception as e:
        st.error(f"Error listing S3 analyses: {str(e)}")
        return []

def download_s3_analysis(s3_key):
    """Download and parse analysis JSON from S3"""
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()
    
    if not s3_client or not bucket_name:
        return None
    
    try:
        # Download JSON from S3
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        content = file_obj['Body'].read().decode('utf-8')
        analysis_data = json.loads(content)
        return analysis_data
    except Exception as e:
        st.error(f"Error downloading analysis: {str(e)}")
        return None

def generate_s3_presigned_url(s3_key, expiration=3600):
    """Generate a presigned URL for S3 object (for audio playback)"""
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()
    
    if not s3_client or not bucket_name:
        return None
    
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        st.error(f"Error generating presigned URL: {str(e)}")
        return None

def get_s3_analysis(record_id, rm_name, call_date):
    """Retrieve analysis JSON from S3 for a specific call"""
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()
    
    if not s3_client or not bucket_name:
        return None
    
    try:
        # Search for analysis JSON in S3
        prefix = f"recordings/analysis/"
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        
        if 'Contents' not in response:
            return None
        
        # Find matching analysis file
        for obj in response['Contents']:
            key = obj['Key']
            if f"analysis_{record_id}_" in key or (rm_name.replace(' ', '_') in key and call_date in key):
                # Download and parse JSON
                file_obj = s3_client.get_object(Bucket=bucket_name, Key=key)
                content = file_obj['Body'].read().decode('utf-8')
                return json.loads(content)
        
        return None
    except Exception as e:
        st.error(f"Error retrieving S3 analysis: {str(e)}")
        return None

def setup_s3_lifecycle_policy():
    """Setup or verify S3 lifecycle policy for 7-day auto-delete"""
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()
    
    if not s3_client or not bucket_name:
        return False, "S3 client not configured"
    
    try:
        lifecycle_policy = {
            'Rules': [
                {
                    'Id': 'iron-lady-auto-delete-7-days',
                    'Status': 'Enabled',
                    'Prefix': 'recordings/',
                    'Expiration': {
                        'Days': 7
                    }
                }
            ]
        }
        
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_policy
        )
        
        return True, "✅ S3 lifecycle policy configured successfully! Files will auto-delete after 7 days."
    
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def verify_s3_lifecycle_policy():
    """Check if S3 lifecycle policy is active"""
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()
    
    if not s3_client or not bucket_name:
        return None
    
    try:
        response = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        rules = response.get('Rules', [])
        
        for rule in rules:
            if rule.get('Prefix') == 'recordings/' and rule.get('Status') == 'Enabled':
                expiration_days = rule.get('Expiration', {}).get('Days')
                return {
                    'active': True,
                    'days': expiration_days,
                    'rule_id': rule.get('Id')
                }
        
        return {'active': False}
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'NoSuchLifecycleConfiguration':
            return {'active': False, 'error': 'No lifecycle policy found'}
        else:
            return {'active': False, 'error': str(e)}
    except Exception as e:
        return {'active': False, 'error': str(e)}

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

def cleanup_old_records():
    """Auto-delete database records older than 7 days"""
    db = load_db()
    current_time = datetime.now().timestamp()
    seven_days_seconds = 7 * 24 * 60 * 60
    
    # Filter out records older than 7 days
    cleaned_db = []
    deleted_count = 0
    
    for record in db:
        uploaded_at = record.get('uploaded_at')
        if uploaded_at:
            try:
                # Parse ISO format timestamp
                upload_datetime = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
                upload_timestamp = upload_datetime.timestamp()
                
                # Keep if less than 7 days old
                if (current_time - upload_timestamp) < seven_days_seconds:
                    cleaned_db.append(record)
                else:
                    deleted_count += 1
            except:
                # Keep record if timestamp parsing fails
                cleaned_db.append(record)
        else:
            # Keep records without timestamp (shouldn't happen, but safe)
            cleaned_db.append(record)
    
    # Save cleaned database if anything was deleted
    if deleted_count > 0:
        save_db(cleaned_db)
    
    return deleted_count

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
    """Enhanced GPT analysis with robust Iron Lady parameters and case study detection"""
    try:
        if manual_scores:
            return generate_analysis_from_scores(manual_scores, call_type, "Manual scoring with GPT-generated insights")
        
        focus_areas = CALL_TYPE_FOCUS.get(call_type, [])
        
        prompt = f"""{IRON_LADY_CONTEXT}

**YOUR TASK:**
Analyze this {call_type} call based on the Iron Lady methodology. This is a CRITICAL analysis that will be used for RM coaching, so be EXTREMELY DETAILED and SPECIFIC.

**CALL CONTENT:**
{additional_context}

**CRITICAL: IRON LADY CASE STUDIES TO DETECT**
Listen carefully for these SPECIFIC participant names and their stories. If ANY of these names are mentioned, note it explicitly:

**Featured Success Stories (Listen for these EXACT names):**
1. **Neha Aggarwal** - Head Sales CMS IT, 30% hike, met Sheryl Sandberg
2. **Rashmi** - Senior Leader, ₹30L to ₹75L, imposter syndrome overcome
3. **Chandana** - Papad entrepreneur, Taj Hotels contract, orders till 2022
4. **Annapurna** - Founder Emotionalytics, B2B entrepreneur from scratch
5. **Pushpalatha** - Co-Founder Garbhagudi, ₹1.4cr to 100cr valuation
6. **Tejaswini Ramisetti** - QA Lead, 20% hike in 1 month
7. **Anusha Stephen** - Talking Canvas founder, 20x revenue growth
8. **Anjali Iyer** - Big 4, skip-level promotion achieved
9. **Jigisha** - Content writer to brand storyteller, 2x scale
10. **Nilmani Gandhi** - Arbitrator, ODR specialist, global brand
11. **Amala** - Social entrepreneur, raised ₹5L in 3 weeks
12. **Sarika Bharani** - Yoga business, doubled customers in 3 months
13. **Gouthami Reddy** - Professor to green café, 3 catering orders
14. **Dr. Roopashree** - Ayurvedic doctor, viral video 46k views
15. **Smita Anand** - Quality Director, escaped politics, new role
16. **Smita Kulkarni** - Sales trainer, 4x revenue in 3 months
17. **Vijayalakshmi Gadepalli** - IIT Mumbai, promoted to Senior PM
18. **Anupama Padhi** - Dhaani Food founder, 40% revenue increase
19. **Vinaya Shenoy** - Fabric enhancement, doubled customers
20. **Surekha Ritesh** - HR consultant, first 3 batches in 3 months
21. **Prabha Sundar** - DPS Dubai Principal, Power Within program
22. **Prapoorna** - Exploridge founder, brain mapping expert
23. **Poornima SP** - XLRI grad, VP HR with 40% hike goal
24. **Aditi Chauhan** - Football captain, She Kicks academy
25. **Anuradha Sridhar** - Teacher training, Head at Aditya Birla
26. **Malini Gulati** - Deputy Director JGU, double promotion
27. **Anupama Bhoopalam** - Architect, 2 decades furniture design
28. **Sajitha Thomas** - HR strategist, promoted within and outside
29. **Rani Suneela Motru** - Portfolio Manager, innovation approved
30. **Kavana Mayur** - Architect, Ace Business 2020 winner
31. **Leena Kotian** - Financial advisor, scaled with pitching
32. **Yashwanti Talreja** - Yash Investment founder, more clients
33. **Nagachaitanya** - QA Automation Broadcom, promotion in 2 months
34. **Meenakshi Talsera** - Self-worth influencer, life coach
35. **Lakshmi N** - HR consultant, scaled business big time
36. **Bhuvaneshwari** - Doubled revenue in 3 months
37. **Gayathri Bhat** - Education entrepreneur, 40 first customers
38. **Deepshikha Bhowmik** - 65% hike in new job
39. **Chaula Trivedi** - Architect, 10 clients monthly freelance
40. **Anubha Doshi** - Artsphere founder, dance + psychology
41. **Sharmishta Chatterjee** - Data Scientist, Google Developer Expert
42. **Palak Jajoo** - Beauty expert, Leimo brand
43. **Rimjhim Mukherjee** - [Graduate]
44. **Padmini Vedula** - Overachieved by 6 crores in 3 months
45. **Nidhi Gandhi** - Fashion, ₹40L painting sales, Studio N
46. **Anu Somani** - Director CRM Inland World Logistics
47. **Pavithra Krishnamurthy** - [Graduate]
48. **Jareena** - [Graduate]
49. **Umaa Vemula** - UniQ Academy, 10 new branches (beat BHAG of 3)
50. **Bharti Chauhan** - Mrs. United Nations Ambassador, mind trainer
51. **Hemalata** - Network marketer, 6-figure income monthly
52. **Anuradha** - Network marketer, went international
53. **Anjana Sateeshan** - Mathematics educator, 30+ years
54. **Ritu Masand** - Banking operations, 20 years experience
55. **Neetu Punhani** - Tooth Doctor CEO, implant surgery specialist
56. **Ramya Bhaskar** - Academician, education industry
57. **Iva Athavia** - Cancer survivor, raised ₹1 crore for NGO Suadha
58. **Harpreet Kaur** - IT professional, job after 2-year break
59. **Vartika Chaturvedi** - Tourism expert, global citizenship
60. **Lakshmi Srinath** - Filmmaker, started own channel
61. **Srikirti** - Product Manager, double promotion with hike
62. **Roshni Rajshekhar** - [Graduate]
63. **Jayaprabha Rajesh** - Alumni, Covid recovery story
64. **Neetee Pawa** - Cyber Security IBM, 55% hike
65. **Manisha Sharma** - Animation industry
66. **Shital Suryavanshi** - Healer, mind coach, book writer
67. **Harvinder Kaur** - CFO Rajasthan Royals IPL
68. **Naveena Priya Patta** - [Graduate]
69. **Jayantika Ganguly** - Corporate lawyer to stress coach
70. **Ashwini** - CA by profession, 40% growth in 6 months
71. **Rekha Rao** - Director Barclays, was HSBC Senior VP
72. **Neha Shrimali** - POSH trainer, impacted 1 lakh individuals
73. **Shailaja** - CSR Head Tata Motors, 2.5 decades experience
74. **Reshmi Dasgupta** - New job after 8-year break
75. **Harsha Keluskar** - Associate VP HR, created new designation
76. **Suhana** - Assistant Manager, PhD papers published
77. **Dr. Bhavi Mody** - Vrudhi Holistic Healthcare founder
78. **Dr. Raka Ghosh** - IIT Mumbai doctorate, drug design
79. **Shobha Patil** - CEO 1000cr valuation company, 500+ employees
80. **Kratika Jain** - Project Manager, 52% hike in 3 weeks
81. **Aswati Dorje** - DCP Police, gold medalist
82. **Arunima Singh** - CDO Marksmen Media
83. **Roshni Dattagupta** - Global Cyber Security Expert
84. **Dr. Anindya** - Ophthalmologist
85. **Rownmani** - Quality Specialist
86. **Sujata Sumant** - Head Marketing Zee TV, 80% hike
87. **Kavita Duragkar** - KP INN co-founder, 3 investors
88. **Arti Hegganavar** - 100% hike at HCL
89. **Sadhana Chigurupali** - Graphic designer, digital marketing

**27 PRINCIPLES - EXACT NAMES TO DETECT:**
If any of these are mentioned BY EXACT NAME or clear reference, note it:
1. Differentiate Branding
2. Shameless Pitching  
3. Fearless Pricing
4. Power of Community
5. Strategic Networking
6. Authentic Leadership
7. Visibility Amplification
8. Value-Based Selling
9. BHAG / BHAG Mindset / Big Hairy Audacious Goals
10. Imposter Syndrome / Imposter Syndrome Management
11. Confident Communication
12. Premium Positioning
13. Ecosystem Building
14. Thought Leadership
15. Leveraged Growth
16. Time Optimization
17. Delegate & Elevate / Delegation
18. Revenue Diversification
19. Scalable Systems
20. Authority Building
21. Mastermind / Mastermind Power
22. Emotional Intelligence
23. Negotiation / Art of Negotiation
24. Resilience / Resilience Building
25. Executive Presence
26. Decision-Making Framework
27. Legacy / Legacy Creation

**STRICT SCORING RULES WITH EXAMPLES:**

**Rapport Building (0-20):**
- 0-5: Cold, transactional, no name usage, no warmth
- 6-10: Basic greeting, name used 1-2 times, minimal connection
- 11-15: Warm tone, name used 3-4 times, shows empathy, asks personal questions
- 16-18: Excellent warmth, name used 5-6 times, deep empathy, strong personal connection, vulnerability shared
- 19-20: EXCEPTIONAL - name used 7+ times, creates safe space, participant opens up emotionally, feels like trusted friend

**Name Usage Requirement:**
- 0 times = MAX 5 points
- 1-2 times = MAX 10 points  
- 3-4 times = MAX 15 points
- 5-6 times = 16-18 points
- 7+ times = 19-20 points

**Needs Discovery (0-25):**
- 0-6: 0-2 superficial questions, no exploration
- 7-12: 3-5 basic questions, surface-level understanding
- 13-18: 6-8 strategic questions, good exploration of current situation
- 19-22: 9-12 deep questions, explores BHAG, pain points, dreams, fears
- 23-25: 13+ questions with follow-ups, creates "aha moments", participant discovers own needs

**Question Types Required for 20+:**
- Discovery questions (current situation)
- BHAG questions (dreams, goals)
- Pain questions (what's not working)
- Gap questions (what's missing)
- Timeline questions (urgency)
- Commitment questions (readiness)

**Solution Presentation (0-25):**
- 0-6: Program barely mentioned, no structure explained
- 7-12: Basic description, vague benefits
- 13-18: Clear structure, 3-4 solid benefits, some differentiation
- 19-22: Comprehensive presentation: structure, community, outcomes, social proof, ROI, certification
- 23-25: MASTERCLASS - all above PLUS specific customization to participant's situation, paints vivid transformation picture

**Must Include for 20+:**
- Program structure (days, modules)
- Community access
- Specific outcomes/results
- 2+ case studies
- ROI / investment justification
- Next steps

**Objection Handling (0-15):**
- 0-3: Objections dismissed, defensive, or ignored
- 4-7: Acknowledges but doesn't resolve
- 8-11: Good handling with empathy + logic
- 12-13: Excellent handling with empathy + case study + reframe
- 14-15: MASTERFUL - uses objection as opportunity, participant convinces themselves, ends with gratitude

**Closing Technique (0-15):**
- 0-3: No close or very weak "let me know"
- 4-7: Vague next steps, no commitment
- 8-11: Clear next steps stated
- 12-13: "Powerfully invite" language + explicit commitments secured
- 14-15: PERFECT CLOSE - assumptive language, multiple commitments, participant excited and ready

**"Powerfully Invite" Examples:**
- "I powerfully invite you to join us"
- "I invite you powerfully to this journey"
- "I see you in this community"
- Must use word "invite" with power/conviction

**Iron Lady Parameters (each 0-10):**

**Profile Understanding (0-10):**
- 0-3: Surface info only, no depth
- 4-6: Understands current situation and some goals
- 7-8: Deep understanding of background, challenges, aspirations
- 9-10: COMPLETE PICTURE - understands participant's unique context, family situation, fears, dreams, timeline

**Credibility Building (0-10):**
- 0-3: No community/results mentioned
- 4-6: Mentions program exists
- 7-8: Shares 1-2 success stories, mentions community
- 9-10: STRONG CREDIBILITY - 3+ specific success stories with names, talks about alumni network, certification value, mentor access

**Principles Usage (0-10):**
- 0-3: NO principles mentioned by name (MAX 3 even if methodology is good)
- 4-6: 1-2 principles mentioned by exact name
- 7-8: 3-5 principles mentioned by exact name with context
- 9-10: 6+ principles mentioned by exact name, woven naturally into conversation

**CRITICAL: Score based on EXACT NAME MENTIONS, not just concepts!**

**Case Studies Usage (0-10):**
- 0-3: NO specific names mentioned (MAX 4 even if generic stories shared)
- 4-6: 1 specific participant name with story
- 7-8: 2-3 specific names with transformations
- 9-10: 4+ specific names with detailed before/after stories

**Names Required:** Neha, Rashmi, Chandana, Annapurna, Pushpalatha, Tejaswini, Priya, Anjali, Meera, Kavita, etc.

**Gap Creation (0-10):**
- 0-3: No gap identified
- 4-6: Generic gap mentioned
- 7-8: Specific gap articulated with numbers (revenue, time, impact)
- 9-10: POWERFUL - gap quantified precisely, cost of inaction clear, creates urgency naturally

**BHAG Fine Tuning (0-10):**
- 0-3: No BHAG discussed (MAX 4)
- 4-6: BHAG identified but not expanded
- 7-8: BHAG explored and expanded 2-3x bigger
- 9-10: TRANSFORMATIONAL - initial goal 5-10x bigger, participant sees new possibilities

**Urgency Creation (0-10):**
- 0-3: No urgency, open-ended
- 4-6: Mentions program exists
- 7-8: Limited spots or closing date mentioned
- 9-10: STRONG FOMO - specific numbers (20 spots left), closes Friday, early bird pricing, payment plan ending

**Commitment Getting (0-10):**
- 0-3: No commitments asked (MAX 4)
- 4-6: Vague "think about it"
- 7-8: 1-2 explicit commitments secured
- 9-10: MULTIPLE CLEAR COMMITMENTS - "I'll attend Day 2", "I'll be on follow-up call Tuesday 4pm", "I'll review investment options"

**Contextualisation (0-10):**
- 0-3: Generic pitch, could be anyone
- 4-6: Some personalization
- 7-8: Good customization to participant's situation
- 9-10: PERFECTLY TAILORED - every example, every principle, every case study directly relevant to participant's exact situation

**Excitement Creation (0-10):**
- 0-3: Flat, no energy
- 4-6: Somewhat enthusiastic
- 7-8: Good energy, participant engaged
- 9-10: CONTAGIOUS ENTHUSIASM - participant's voice changes, gets excited, asks more questions, wants to start now

**CRITICAL PENALTIES (ENFORCE STRICTLY):**
- NO principles mentioned by name = Principles Usage MAX 3/10
- NO case study names = Case Studies Usage MAX 4/10
- NO BHAG explored = BHAG Fine Tuning MAX 4/10
- NO commitments = Commitment Getting MAX 4/10
- "Powerfully invite" NOT used = Closing MAX 11/15

**OUTPUT FORMAT - Respond ONLY with this JSON:**

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
    "case_studies_mentioned": [
        "List EXACT names mentioned (e.g., Neha, Rashmi, Chandana, etc.)",
        "If NONE mentioned, return empty array []"
    ],
    "principles_mentioned": [
        "List EXACT principle names mentioned (e.g., Fearless Pricing, BHAG Mindset)",
        "Only include if mentioned BY NAME or clear direct reference",
        "If NONE mentioned by name, return empty array []"
    ],
    "participant_name_usage_count": <exact number of times participant's name was used>,
    "powerfully_invite_used": <true/false - was exact phrase "powerfully invite" or "invite powerfully" used?>,
    "commitments_secured": [
        "List EXPLICIT commitments obtained (e.g., 'Will attend Day 2', 'Follow-up call Tuesday 4pm')",
        "If NONE secured, return empty array []"
    ],
    "bhag_initial": "Participant's initial goal/BHAG stated",
    "bhag_expanded": "Expanded BHAG if RM helped dream bigger (or 'Not expanded' if same)",
    "gap_quantified": "Specific gap identified with numbers if possible",
    "urgency_tactics": ["List urgency tactics used: limited spots, closing date, etc."],
    "call_quality_summary": "2-3 sentences summarizing the OVERALL QUALITY of this call. What made it good or bad? Be specific about what the RM did well and what they missed. Mention SPECIFIC moments from the call.",
    "justification": "1-2 sentences explaining the scores. Focus on the MOST CRITICAL gaps or strengths."
}}

**BE STRICT**: Most calls will score 50-70/100. Only truly exceptional calls following ALL guidelines score 80+. Don't be generous - be accurate and help RMs improve."""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert Iron Lady call analyst. You are STRICT and ACCURATE. You score based on what was ACTUALLY SAID, not what should have been said. You ALWAYS detect and list case study names and principle names if mentioned. You count participant name usage precisely. You are training RMs to be excellent, so your feedback must be honest and specific."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        analysis_text = response.choices[0].message.content
        scores_data = json.loads(analysis_text)
        
        # Extract metadata for enhanced tracking
        metadata = {
            "case_studies_mentioned": scores_data.get('case_studies_mentioned', []),
            "principles_mentioned": scores_data.get('principles_mentioned', []),
            "participant_name_usage_count": scores_data.get('participant_name_usage_count', 0),
            "powerfully_invite_used": scores_data.get('powerfully_invite_used', False),
            "commitments_secured": scores_data.get('commitments_secured', []),
            "bhag_initial": scores_data.get('bhag_initial', "Not captured"),
            "bhag_expanded": scores_data.get('bhag_expanded', "Not expanded"),
            "gap_quantified": scores_data.get('gap_quantified', "Not quantified"),
            "urgency_tactics": scores_data.get('urgency_tactics', [])
        }
        
        # Use improved call quality summary from GPT
        call_summary = scores_data.get('call_quality_summary', scores_data.get('justification', 'GPT analysis based on Iron Lady methodology'))
        
        return generate_analysis_from_scores(
            scores_data.get('core_dimensions', {}),
            call_type,
            call_summary,
            scores_data.get('iron_lady_parameters', {}),
            metadata  # Pass metadata
        )
    except Exception as e:
        st.error(f"GPT Error: {str(e)}")
        return generate_analysis_from_scores({
            "rapport_building": 10, "needs_discovery": 12, "solution_presentation": 12,
            "objection_handling": 8, "closing_technique": 8
        }, call_type, f"Error: {str(e)}")

def generate_analysis_from_scores(core_dims, call_type, justification, il_params=None, metadata=None):
    """Generate complete analysis from scores with enhanced tracking"""
    
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
    
    # Enhanced metadata tracking
    if metadata is None:
        metadata = {}
    
    enhanced_metadata = {
        "case_studies_mentioned": metadata.get("case_studies_mentioned", []),
        "principles_mentioned": metadata.get("principles_mentioned", []),
        "participant_name_usage_count": metadata.get("participant_name_usage_count", 0),
        "powerfully_invite_used": metadata.get("powerfully_invite_used", False),
        "commitments_secured": metadata.get("commitments_secured", []),
        "bhag_initial": metadata.get("bhag_initial", "Not captured"),
        "bhag_expanded": metadata.get("bhag_expanded", "Not expanded"),
        "gap_quantified": metadata.get("gap_quantified", "Not quantified"),
        "urgency_tactics": metadata.get("urgency_tactics", [])
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
    
    # Add special coaching for case studies and principles
    if enhanced_metadata['case_studies_mentioned']:
        best_moments.append(f"✅ Case studies used: {', '.join(enhanced_metadata['case_studies_mentioned'][:3])}")
    else:
        critical_gaps.append("❌ NO case study names mentioned")
        il_coaching.insert(0, "🚨 CRITICAL: Use specific names (Neha, Rashmi, Chandana)")
    
    if enhanced_metadata['principles_mentioned']:
        best_moments.append(f"✅ Principles used: {', '.join(enhanced_metadata['principles_mentioned'][:3])}")
    else:
        critical_gaps.append("❌ NO principles mentioned by name")
        il_coaching.insert(0, "🚨 CRITICAL: Mention principles by exact name (e.g., 'Fearless Pricing')")
    
    if enhanced_metadata['powerfully_invite_used']:
        best_moments.append("✅ Used 'Powerfully Invite' language")
    else:
        missed_opportunities.append("❌ Did NOT use 'Powerfully Invite'")
        il_coaching.append("Say: 'I powerfully invite you to join this journey'")
    
    if enhanced_metadata['commitments_secured']:
        best_moments.append(f"✅ Secured {len(enhanced_metadata['commitments_secured'])} commitments")
    
    if enhanced_metadata['participant_name_usage_count'] >= 5:
        best_moments.append(f"✅ Used participant name {enhanced_metadata['participant_name_usage_count']} times")
    elif enhanced_metadata['participant_name_usage_count'] > 0:
        missed_opportunities.append(f"⚠️ Only used name {enhanced_metadata['participant_name_usage_count']} times (need 5+)")
    else:
        critical_gaps.append("❌ Participant name NOT used")
    
    # Build highlighted summary with case studies
    summary = f"{call_type} scored {overall_score:.1f}/100 with {methodology_compliance:.1f}% IL compliance. {justification}"
    
    # Add case study highlights if any were mentioned
    if enhanced_metadata['case_studies_mentioned']:
        case_studies_str = ", ".join(enhanced_metadata['case_studies_mentioned'])
        summary += f" 🌟 Case studies mentioned: {case_studies_str}."
    
    return {
        "overall_score": round(overall_score, 1),
        "methodology_compliance": round(methodology_compliance, 1),
        "call_effectiveness": effectiveness,
        "core_dimensions": core_dimensions,
        "iron_lady_parameters": iron_lady_parameters,
        "enhanced_tracking": enhanced_metadata,  # NEW: Enhanced tracking data
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

# Auto-cleanup old records (7+ days)
try:
    deleted_count = cleanup_old_records()
    if deleted_count > 0:
        st.toast(f"🗑️ Auto-cleaned {deleted_count} records older than 7 days")
except Exception as e:
    pass  # Silent fail on cleanup errors

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
        
        # Check lifecycle policy status (display only, no setup button)
        try:
            lifecycle_status = verify_s3_lifecycle_policy()
            if lifecycle_status:
                if lifecycle_status.get('active'):
                    days = lifecycle_status.get('days', 7)
                    st.sidebar.success(f"🗑️ Auto-delete: {days} days ✅")
                else:
                    st.sidebar.warning("⚠️ Auto-delete: Not configured")
            else:
                st.sidebar.caption("🗑️ Auto-delete: Checking...")
        except Exception as e:
            st.sidebar.caption("🗑️ Auto-delete: Check in S3 Browser")
    else:
        st.sidebar.warning("S3 stats unavailable")
except Exception as e:
    st.sidebar.error("⚠️ S3 not configured")
    st.sidebar.caption("Add AWS credentials to secrets")

# Database auto-cleanup status
st.sidebar.markdown("---")
st.sidebar.markdown("### 🗄️ Database")
try:
    db = load_db()
    st.sidebar.info(f"**Records:** {len(db)}")
    st.sidebar.caption("🗑️ Auto-cleanup: 7 days")
except:
    st.sidebar.caption("Database initializing...")

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
                    # Color-coded quality only (no numbers)
                    if analysis['overall_score'] >= 80:
                        st.success("### ✅ Excellent Call")
                    elif analysis['overall_score'] >= 65:
                        st.info("### 🟡 Good Call")
                    else:
                        st.error("### ❌ Needs Improvement")
                
                with col2:
                    # IL Compliance as color
                    if analysis['methodology_compliance'] >= 75:
                        st.success("✅ Strong IL Adherence")
                    elif analysis['methodology_compliance'] >= 55:
                        st.warning("🟡 Moderate IL Usage")
                    else:
                        st.error("❌ Weak IL Methodology")
                
                with col3:
                    effectiveness = analysis['call_effectiveness']
                    if effectiveness == "Excellent":
                        st.success(f"✅ {effectiveness}")
                    elif effectiveness == "Good":
                        st.info(f"🟡 {effectiveness}")
                    else:
                        st.warning(f"⚠️ {effectiveness}")
                
                with col4:
                    pred_emoji = {"registration_expected": "🎉", "follow_up_needed": "📞", "needs_improvement": "⚠️"}
                    pred_result = analysis['outcome_prediction']['likely_result']
                    pred_display = pred_result.replace('_', ' ').title()
                    
                    if pred_result == "registration_expected":
                        st.success(f"🎉 {pred_display}")
                    elif pred_result == "follow_up_needed":
                        st.info(f"📞 {pred_display}")
                    else:
                        st.warning(f"⚠️ {pred_display}")
                
                st.markdown("**Executive Summary:**")
                st.info(analysis['call_summary'])
                
                # HIGHLIGHT Case Studies & Principles (NEW!)
                if 'enhanced_tracking' in analysis:
                    track = analysis['enhanced_tracking']
                    
                    # Show prominent highlights if any were used
                    if track['case_studies_mentioned'] or track['principles_mentioned']:
                        st.markdown("---")
                        col_highlight1, col_highlight2 = st.columns(2)
                        
                        with col_highlight1:
                            if track['case_studies_mentioned']:
                                st.success("### 🌟 Case Studies Used in This Call")
                                for case in track['case_studies_mentioned']:
                                    st.markdown(f"### ✅ **{case}**")
                                st.caption(f"Total: {len(track['case_studies_mentioned'])} success stories shared")
                            else:
                                st.error("### ❌ No Case Studies Mentioned")
                                st.caption("Use names: Neha, Rashmi, Chandana, Annapurna, etc.")
                        
                        with col_highlight2:
                            if track['principles_mentioned']:
                                st.success("### 💎 Principles Used in This Call")
                                for principle in track['principles_mentioned']:
                                    st.markdown(f"### ✅ **{principle}**")
                                st.caption(f"Total: {len(track['principles_mentioned'])} principles by name")
                            else:
                                st.error("### ❌ No Principles by Name")
                                st.caption("Say: 'Fearless Pricing', 'BHAG Mindset', etc.")
                
                # Enhanced Tracking Section
                if 'enhanced_tracking' in analysis:
                    st.markdown("---")
                    st.markdown("### 🎯 Iron Lady Methodology Tracking")
                    
                    track = analysis['enhanced_tracking']
                    
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.markdown("**📚 Case Studies Used:**")
                        if track['case_studies_mentioned']:
                            for case in track['case_studies_mentioned']:
                                st.success(f"✅ {case}")
                            st.caption(f"Total: {len(track['case_studies_mentioned'])} case studies")
                        else:
                            st.error("❌ NO case studies mentioned")
                            st.caption("🚨 CRITICAL: Use names like Neha, Rashmi, Chandana")
                    
                    with col_b:
                        st.markdown("**💎 27 Principles Used:**")
                        if track['principles_mentioned']:
                            for principle in track['principles_mentioned']:
                                st.success(f"✅ {principle}")
                            st.caption(f"Total: {len(track['principles_mentioned'])} principles")
                        else:
                            st.error("❌ NO principles by name")
                            st.caption("🚨 CRITICAL: Say exact names (e.g., 'Fearless Pricing')")
                    
                    with col_c:
                        st.markdown("**🎤 Engagement Tracking:**")
                        
                        # Name usage
                        name_count = track.get('participant_name_usage_count', 0)
                        if name_count >= 5:
                            st.success(f"✅ Name used {name_count} times")
                        elif name_count > 0:
                            st.warning(f"⚠️ Name used only {name_count} times")
                            st.caption("Target: 5+ times")
                        else:
                            st.error("❌ Name NOT used")
                        
                        # Powerfully invite
                        if track.get('powerfully_invite_used'):
                            st.success("✅ 'Powerfully Invite' used")
                        else:
                            st.error("❌ 'Powerfully Invite' NOT used")
                        
                        # Commitments
                        commits = track.get('commitments_secured', [])
                        if commits:
                            st.success(f"✅ {len(commits)} commitments secured")
                        else:
                            st.error("❌ NO commitments secured")
                    
                    # BHAG and Gap (expandable)
                    with st.expander("🎯 BHAG & Gap Analysis", expanded=False):
                        col_x, col_y = st.columns(2)
                        with col_x:
                            st.markdown("**BHAG Journey:**")
                            st.write(f"**Initial:** {track.get('bhag_initial', 'Not captured')}")
                            st.write(f"**Expanded:** {track.get('bhag_expanded', 'Not expanded')}")
                            if track.get('bhag_expanded') != 'Not expanded' and track.get('bhag_expanded') != track.get('bhag_initial'):
                                st.success("✅ BHAG expanded successfully")
                            else:
                                st.warning("⚠️ BHAG not expanded")
                        
                        with col_y:
                            st.markdown("**Gap & Urgency:**")
                            st.write(f"**Gap:** {track.get('gap_quantified', 'Not quantified')}")
                            urgency = track.get('urgency_tactics', [])
                            if urgency:
                                st.write("**Urgency tactics:**")
                                for tactic in urgency:
                                    st.write(f"• {tactic}")
                            else:
                                st.warning("⚠️ No urgency created")
                    
                    # Commitments detail (expandable)
                    if commits:
                        with st.expander("✅ Commitments Secured", expanded=False):
                            for i, commit in enumerate(commits, 1):
                                st.write(f"{i}. {commit}")
                
                st.markdown("---")
                
                # Core Dimensions - CHECKBOX DISPLAY (NO SCORES)
                st.markdown("### 🎯 Core Dimensions")
                
                col_cd1, col_cd2 = st.columns(2)
                
                core_items = list(analysis['core_dimensions'].items())
                core_mid = len(core_items) // 2
                
                with col_cd1:
                    for param, score in core_items[:core_mid]:
                        param_name = param.replace('_', ' ').title()
                        max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][param]["weight"]
                        percentage = (score / max_score) * 100
                        
                        # Three-tier system for core dimensions too
                        if percentage >= 75:
                            checkbox = "✅"  # Green - Excellent
                            color = "green"
                        elif percentage >= 55:
                            checkbox = "🟡"  # Yellow - Adequate
                            color = "orange"
                        else:
                            checkbox = "❌"  # Red - Poor
                            color = "red"
                        
                        st.markdown(f":{color}[{checkbox} **{param_name}**]")
                
                with col_cd2:
                    for param, score in core_items[core_mid:]:
                        param_name = param.replace('_', ' ').title()
                        max_score = IRON_LADY_PARAMETERS["Core Quality Dimensions"][param]["weight"]
                        percentage = (score / max_score) * 100
                        
                        # Three-tier system
                        if percentage >= 75:
                            checkbox = "✅"  # Green - Excellent
                            color = "green"
                        elif percentage >= 55:
                            checkbox = "🟡"  # Yellow - Adequate
                            color = "orange"
                        else:
                            checkbox = "❌"  # Red - Poor
                            color = "red"
                        
                        st.markdown(f":{color}[{checkbox} **{param_name}**]")
                
                st.markdown("---")
                
                # IL Parameters - CHECKBOX DISPLAY (NEW!)
                st.markdown("### 💎 Iron Lady Parameters Checklist")
                
                # Create checkbox grid
                col1, col2 = st.columns(2)
                
                il_params_list = list(analysis['iron_lady_parameters'].items())
                mid_point = len(il_params_list) // 2
                
                with col1:
                    for param, score in il_params_list[:mid_point]:
                        param_name = param.replace('_', ' ').title()
                        
                        # Determine checkbox based on score
                        if score >= 7:
                            checkbox = "✅"  # Green tick - Good
                            color = "green"
                        elif score >= 5:
                            checkbox = "🟡"  # Yellow - Adequate
                            color = "orange"
                        else:
                            checkbox = "❌"  # Red X - Poor
                            color = "red"
                        
                        # Display with color (NO SCORE NUMBERS)
                        st.markdown(f":{color}[{checkbox} **{param_name}**]")
                
                with col2:
                    for param, score in il_params_list[mid_point:]:
                        param_name = param.replace('_', ' ').title()
                        
                        # Determine checkbox based on score
                        if score >= 7:
                            checkbox = "✅"  # Green tick - Good
                            color = "green"
                        elif score >= 5:
                            checkbox = "🟡"  # Yellow - Adequate
                            color = "orange"
                        else:
                            checkbox = "❌"  # Red X - Poor
                            color = "red"
                        
                        # Display with color (NO SCORE NUMBERS)
                        st.markdown(f":{color}[{checkbox} **{param_name}**]")
                
                # Summary stats
                st.markdown("---")
                excellent = sum(1 for score in analysis['iron_lady_parameters'].values() if score >= 7)
                adequate = sum(1 for score in analysis['iron_lady_parameters'].values() if 5 <= score < 7)
                poor = sum(1 for score in analysis['iron_lady_parameters'].values() if score < 5)
                total = len(analysis['iron_lady_parameters'])
                
                col_x, col_y, col_z, col_w = st.columns(4)
                with col_x:
                    st.metric("✅ Excellent (≥7)", f"{excellent}/{total}")
                with col_y:
                    st.metric("🟡 Adequate (5-6)", f"{adequate}/{total}")
                with col_z:
                    st.metric("❌ Poor (<5)", f"{poor}/{total}")
                with col_w:
                    pass_rate = ((excellent + adequate) / total) * 100
                    if pass_rate >= 80:
                        st.success(f"🌟 {pass_rate:.0f}% Pass")
                    elif pass_rate >= 60:
                        st.info(f"👍 {pass_rate:.0f}% Pass")
                    else:
                        st.warning(f"⚠️ {pass_rate:.0f}% Pass")
                
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
                
                # Case Studies & Principles Checklist (NEW!)
                if 'enhanced_tracking' in analysis:
                    st.markdown("---")
                    st.markdown("**🎯 Methodology Checklist:**")
                    
                    track = analysis['enhanced_tracking']
                    col_cs, col_pr = st.columns(2)
                    
                    with col_cs:
                        case_studies = track.get('case_studies_mentioned', [])
                        if case_studies:
                            st.success(f"✅ Case Studies: {', '.join(case_studies[:2])}")
                        else:
                            st.error("❌ No case studies used")
                    
                    with col_pr:
                        principles = track.get('principles_mentioned', [])
                        if principles:
                            st.success(f"✅ Principles: {', '.join(principles[:2])}")
                        else:
                            st.error("❌ No principles by name")
                    
                    # Key methodology checks
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        if track.get('powerfully_invite_used'):
                            st.success("✅ 'Powerfully Invite' used")
                        else:
                            st.error("❌ 'Powerfully Invite' missing")
                    
                    with col_m2:
                        commits = len(track.get('commitments_secured', []))
                        if commits > 0:
                            st.success(f"✅ {commits} commitments secured")
                        else:
                            st.error("❌ No commitments secured")
                
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
    
    # Create tabs for Database and S3
    tab_db, tab_s3_analysis, tab_s3_audio = st.tabs(["📊 Database Records", "📦 S3 Analysis JSONs", "🎤 S3 Audio Files"])
    
    # TAB 1: Database Records (Original Admin View)
    with tab_db:
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
    
    # TAB 2: S3 Analysis JSONs
    with tab_s3_analysis:
        st.subheader("📦 AWS S3 Analysis Browser")
        
        # Check S3 connection
        s3_stats = get_s3_stats()
        if not s3_stats:
            st.error("❌ AWS S3 not connected. Please configure AWS credentials in Streamlit secrets.")
            st.stop()
        
        # S3 Status metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total S3 Files", s3_stats['files'])
        with col2:
            st.metric("Storage Used", s3_stats['size'])
        with col3:
            try:
                lifecycle_status = verify_s3_lifecycle_policy()
                if lifecycle_status and lifecycle_status.get('active'):
                    days = lifecycle_status.get('days', 7)
                    st.metric("Auto-Delete", f"{days} days ✅", delta="Active")
                else:
                    st.metric("Auto-Delete", "Not Set", delta="Setup in AWS Console", delta_color="inverse")
            except:
                st.metric("Auto-Delete", "Unknown", delta="Check AWS Console")
        
        st.markdown("---")
        st.caption("📁 **S3 Path:** `recordings/analysis/YYYY/MM/DD/*.json`")
        
        with st.spinner("Loading analysis files from S3..."):
            analyses = list_s3_analyses()
        
        if not analyses:
            st.info("No analysis JSONs found in S3. Upload and analyze calls to see them here.")
        else:
            st.success(f"Found **{len(analyses)}** analysis files in S3")
            
            # Search
            search = st.text_input("🔍 Search by filename", placeholder="e.g., analysis_15_Priya", key="search_s3_analysis")
            
            if search:
                analyses = [a for a in analyses if search.lower() in a['filename'].lower()]
                st.caption(f"Showing {len(analyses)} matching analyses")
            
            # Display analyses
            st.markdown("---")
            for idx, analysis in enumerate(analyses[:50]):
                days_old = (datetime.now(analysis['last_modified'].tzinfo) - analysis['last_modified']).days
                
                if days_old >= 7:
                    color = "🔴"
                    status = "Scheduled for deletion"
                elif days_old >= 4:
                    color = "🟡"
                    status = "Expires soon"
                else:
                    color = "🟢"
                    status = "Fresh"
                
                with st.expander(f"{color} {analysis['filename']} - {status} ({days_old} days old)"):
                    col_a, col_b = st.columns([3, 2])
                    
                    with col_a:
                        st.write(f"**📁 S3 Path:**")
                        st.code(analysis['key'], language="text")
                        st.write(f"**📅 Uploaded:** {analysis['last_modified'].strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"**📊 Size:** {analysis['size'] / 1024:.1f} KB")
                        st.write(f"**⏰ Age:** {days_old} days")
                    
                    with col_b:
                        if st.button("📥 Download & View", key=f"dl_s3_{idx}", use_container_width=True):
                            with st.spinner("Downloading from S3..."):
                                analysis_data = download_s3_analysis(analysis['key'])
                            
                            if analysis_data:
                                st.success("✅ Downloaded!")
                                json_str = json.dumps(analysis_data, indent=2)
                                st.download_button(
                                    label="💾 Save JSON",
                                    data=json_str,
                                    file_name=analysis['filename'],
                                    mime="application/json",
                                    key=f"save_json_{idx}"
                                )
                    
                    # Preview
                    if f"preview_s3_{idx}" in st.session_state or st.button("👁️ Preview", key=f"prev_{idx}"):
                        st.session_state[f"preview_s3_{idx}"] = True
                        
                        with st.spinner("Loading..."):
                            analysis_data = download_s3_analysis(analysis['key'])
                        
                        if analysis_data:
                            st.markdown("---")
                            st.markdown("### 📊 Analysis Preview")
                            
                            record_data = analysis_data
                            analysis_results = record_data.get('analysis', {})
                            
                            info_col1, info_col2, info_col3 = st.columns(3)
                            with info_col1:
                                st.metric("RM", record_data.get('rm_name', 'N/A'))
                            with info_col2:
                                st.metric("Participant", record_data.get('client_name', 'N/A'))
                            with info_col3:
                                overall_score = analysis_results.get('overall_score', 0)
                                st.metric("Score", f"{overall_score:.1f}/100")
                            
                            st.write(f"**Call Type:** {record_data.get('call_type', 'N/A')}")
                            st.write(f"**Date:** {record_data.get('call_date', 'N/A')}")
                            st.write(f"**Outcome:** {record_data.get('pitch_outcome', 'N/A')}")
                            
                            with st.expander("📈 Detailed Scores"):
                                core = analysis_results.get('core_dimensions', {})
                                iron_lady = analysis_results.get('iron_lady_parameters', {})
                                
                                col_score1, col_score2 = st.columns(2)
                                with col_score1:
                                    st.markdown("**🎯 Core Dimensions**")
                                    for param, score in core.items():
                                        st.write(f"• {param.replace('_', ' ').title()}: {score}")
                                
                                with col_score2:
                                    st.markdown("**💎 Iron Lady Parameters**")
                                    for param, score in iron_lady.items():
                                        st.write(f"• {param.replace('_', ' ').title()}: {score}")
                            
                            if analysis_results.get('strengths'):
                                with st.expander("✅ Strengths"):
                                    for strength in analysis_results['strengths']:
                                        st.write(f"• {strength}")
                            
                            if analysis_results.get('areas_for_improvement'):
                                with st.expander("📈 Improvements"):
                                    for area in analysis_results['areas_for_improvement']:
                                        st.write(f"• {area}")
                            
                            with st.expander("🔍 Full JSON"):
                                st.json(analysis_data)
            
            if len(analyses) > 50:
                st.info(f"Showing 50 of {len(analyses)} analyses. Use search to find more.")
    
    # TAB 3: S3 Audio Recordings
    with tab_s3_audio:
        st.subheader("🎤 AWS S3 Audio Recordings")
        st.caption("📁 **S3 Path:** `recordings/YYYY/MM/DD/*.mp3`")
        
        with st.spinner("Loading audio files from S3..."):
            recordings = list_s3_recordings()
        
        if not recordings:
            st.info("No audio recordings found in S3.")
        else:
            st.success(f"Found **{len(recordings)}** audio recordings in S3")
            
            # Search
            search_audio = st.text_input("🔍 Search by filename", placeholder="e.g., Priya_Sharma", key="search_s3_audio")
            
            if search_audio:
                recordings = [r for r in recordings if search_audio.lower() in r['filename'].lower()]
                st.caption(f"Showing {len(recordings)} matching recordings")
            
            st.markdown("---")
            
            # Display recordings with audio players
            for idx, rec in enumerate(sorted(recordings, key=lambda x: x['last_modified'], reverse=True)[:50]):
                days_old = (datetime.now(rec['last_modified'].tzinfo) - rec['last_modified']).days
                
                if days_old >= 7:
                    status_icon = "🔴"
                    status_text = "Will delete"
                elif days_old >= 4:
                    status_icon = "🟡"
                    status_text = "Expiring soon"
                else:
                    status_icon = "🟢"
                    status_text = "Fresh"
                
                size_display = f"{rec['size'] / (1024*1024):.2f} MB" if rec['size'] > 1024*1024 else f"{rec['size'] / 1024:.2f} KB"
                
                with st.expander(f"{status_icon} {rec['filename']} - {size_display} - {status_text} ({days_old} days old)"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**📁 Filename:** {rec['filename']}")
                        st.write(f"**📅 Uploaded:** {rec['last_modified'].strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"**📊 Size:** {size_display}")
                        st.write(f"**⏰ Age:** {days_old} days")
                        st.write(f"**🎯 Status:** {status_text}")
                        st.caption(f"S3 Path: `{rec['key']}`")
                    
                    with col2:
                        st.write("**🎧 Audio Controls:**")
                        
                        # Auto-generate URL on expand
                        if f"audio_url_{idx}" not in st.session_state:
                            with st.spinner("Loading audio..."):
                                audio_url = generate_s3_presigned_url(rec['key'], expiration=3600)
                                if audio_url:
                                    st.session_state[f"audio_url_{idx}"] = audio_url
                        
                        # Download button
                        if f"audio_url_{idx}" in st.session_state:
                            audio_url = st.session_state[f"audio_url_{idx}"]
                            st.markdown(f"[📥 Download Audio]({audio_url})")
                            
                            # Refresh URL button
                            if st.button("🔄 Refresh Link", key=f"refresh_{idx}", use_container_width=True):
                                audio_url = generate_s3_presigned_url(rec['key'], expiration=3600)
                                if audio_url:
                                    st.session_state[f"audio_url_{idx}"] = audio_url
                                    st.success("✅ Link refreshed!")
                                    st.rerun()
                    
                    # Display audio player prominently
                    if f"audio_url_{idx}" in st.session_state:
                        st.markdown("---")
                        st.markdown("### 🎧 Play Audio Recording")
                        
                        audio_url = st.session_state[f"audio_url_{idx}"]
                        
                        # Display audio player
                        st.audio(audio_url, format='audio/mp3')
                        
                        st.caption("💡 Audio link expires in 1 hour. Click 'Refresh Link' to generate a new one.")
                    else:
                        st.warning("⚠️ Could not load audio. Click 'Refresh Link' to try again.")
            
            st.markdown("---")
            st.markdown("""
            **Legend:** 
            - 🟢 **Fresh** (0-3 days) - Recently uploaded
            - 🟡 **Expiring** (4-6 days) - Will be deleted in 1-3 days
            - 🔴 **Will delete** (7+ days) - Scheduled for deletion
            """)
            
            st.caption(f"💡 Showing {min(len(recordings), 50)} most recent recordings")
            st.caption("🎵 Click 'Play Audio' to listen to any recording in the app")

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
