# 📧 Email Importance Analysis Logic

## 🎯 **Overview**
The AI Voice Agent analyzes emails from the last **24 hours** using a sophisticated multi-layered importance scoring system that combines AI-powered analysis with rule-based fallbacks.

## ⏰ **Email Fetching Strategy**

### **24-Hour Window**
```python
# Always fetch emails from last 24 hours
since_24h = datetime.now() - timedelta(hours=24)
query = f"after:{date_str} -in:spam -in:trash"
```

**Why 24 hours?**
- ✅ Captures all recent activity without overwhelming the system
- ✅ Ensures urgent emails aren't missed
- ✅ Balances comprehensiveness with performance
- ✅ Aligns with typical business communication patterns

## 🧠 **Importance Analysis Logic**

### **Primary Analysis: LLM-Based**
The system uses a free LLM (Ollama/Groq) with a structured prompt to analyze each email:

```python
prompt = """
Analyze this email and provide a JSON response:
- importance_score: float (0.0 to 1.0, where 1.0 is most important)
- requires_action: boolean
- action_type: "reply", "schedule", "urgent", "delegate", "archive", null
- urgency: "low", "medium", "high", "critical"
- summary: brief summary of email content
- suggested_action: what action to take, if any

Consider factors like:
- Sender importance (boss, client, family)
- Subject urgency keywords (urgent, asap, deadline)
- Content requesting meetings, decisions, or immediate response
- Time-sensitive information
"""
```

### **Scoring Factors Analyzed by LLM:**

#### **1. Sender Authority & Relationship** (Weight: High)
- **Boss/CEO/Director**: +0.3 importance boost
- **Clients/Customers**: +0.25 importance boost
- **Family/Personal**: Context-dependent scoring
- **Unknown senders**: Lower baseline score

#### **2. Subject Line Keywords** (Weight: High)
- **Urgent indicators**: "URGENT", "ASAP", "DEADLINE", "IMMEDIATE"
- **Meeting requests**: "MEETING", "SCHEDULE", "CALENDAR"
- **Decision required**: "DECISION", "APPROVAL", "REVIEW"
- **Time-sensitive**: "TODAY", "TOMORROW", "EOD"

#### **3. Content Analysis** (Weight: Medium-High)
- **Action requests**: Emails asking for specific actions
- **Questions**: Direct questions requiring responses
- **Meeting invitations**: Calendar requests
- **Deadline mentions**: Time-sensitive content
- **Escalation**: Issues being escalated

#### **4. Context Clues** (Weight: Medium)
- **Reply chains**: Ongoing conversations have higher importance
- **CC vs TO**: Direct recipients vs CC recipients
- **Internal vs External**: Company emails vs external

## 🛡️ **Fallback Scoring System**
When LLM analysis fails, a rule-based system provides backup scoring:

### **Fallback Logic**
```python
def _parse_email_fallback(email_data, response):
    importance_score = 0.3  # baseline
    
    # Subject line analysis
    urgent_keywords = ['urgent', 'asap', 'important', 'deadline']
    if any(word in subject.lower() for word in urgent_keywords):
        importance_score += 0.4
    
    # Sender domain analysis
    if any(domain in sender for domain in ['boss', 'ceo', 'director']):
        importance_score += 0.3
    
    return {
        'importance_score': min(importance_score, 1.0),
        'requires_action': importance_score > 0.6,
        'urgency': 'high' if importance_score > 0.8 else 'medium',
        'suggested_action': 'Review and respond' if important else None
    }
```

## 📊 **Importance Score Interpretation**

### **Score Ranges**
- **0.0 - 0.3**: Low importance (newsletters, notifications)
- **0.3 - 0.6**: Medium importance (regular work emails)
- **0.6 - 0.8**: High importance (requires attention)
- **0.8 - 1.0**: Critical importance (immediate action needed)

### **Action Thresholds**
- **< 0.6**: Monitor only, no immediate action
- **≥ 0.6**: Flag for user attention
- **≥ 0.7**: Add to "important items" list
- **≥ 0.8**: Trigger voice call to user (if enabled)

## 🎭 **Action Type Classification**

### **Action Categories**
1. **"reply"**: Email requires a response
2. **"schedule"**: Meeting/calendar request
3. **"urgent"**: Immediate attention needed
4. **"delegate"**: Can be forwarded to others
5. **"archive"**: Informational, no action needed

### **Urgency Levels**
1. **"critical"**: Business-critical, immediate action (< 1 hour)
2. **"high"**: Important, same day response needed
3. **"medium"**: Normal business, respond within 24-48 hours
4. **"low"**: Informational, respond when convenient

## 🔄 **Batch Processing**
```python
async def analyze_email_batch(emails):
    results = []
    for email in emails:
        try:
            result = await service.analyze_email(email)
            results.append(result)
        except Exception:
            # Fallback to rule-based analysis
            results.append(service._parse_email_fallback(email, ""))
    return results
```

## 🚨 **User Notification Triggers**

### **Voice Call Conditions**
- Any email with `importance_score ≥ 0.8`
- Urgent emails from known contacts
- Meeting conflicts detected
- More than 3 high-priority emails in one batch

### **Dashboard Alerts**
- High-priority emails appear in "Important Items"
- Color-coded urgency indicators
- Suggested actions displayed
- One-click response options

## 🧪 **Example Scenarios**

### **Critical Email (Score: 0.9)**
```
From: boss@company.com
Subject: URGENT: Client presentation deadline moved to TODAY
Content: "Need the slides by 2 PM for emergency client meeting..."

Result:
- importance_score: 0.9
- urgency: "critical"
- action_type: "urgent"
- suggested_action: "Prepare slides immediately"
→ Triggers voice call to user
```

### **Medium Email (Score: 0.5)**
```
From: newsletter@service.com
Subject: Weekly Update: New Features Released
Content: "This week we launched several new features..."

Result:
- importance_score: 0.5
- urgency: "low"
- action_type: "archive"
- suggested_action: null
→ No user notification
```

### **High Priority Email (Score: 0.75)**
```
From: client@important-customer.com
Subject: Question about project timeline
Content: "Could you clarify the delivery date for Phase 2?"

Result:
- importance_score: 0.75
- urgency: "high"
- action_type: "reply"
- suggested_action: "Respond with timeline details"
→ Added to important items list
```

## ⚙️ **Configuration Options**

### **Adjustable Parameters**
- `importance_threshold`: Minimum score for user notification (default: 0.7)
- `critical_threshold`: Score for immediate voice calls (default: 0.8)
- `batch_size`: Number of emails to analyze at once (default: 50)
- `analysis_timeout`: Max time for LLM analysis (default: 60 seconds)

This multi-layered approach ensures reliable email importance detection even when AI services are unavailable, while providing sophisticated analysis when they are working optimally! 🎯