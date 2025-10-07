# Fireflies Transcript Structure & Timestamp Analysis

## Complete Understanding: Webhook Push vs Transcript Session

### **Key Clarification: What is a "Transcript"?**

Based on analysis of the actual Fireflies JSON file (`Membership-Home-Big-Picture-Trading-mp4-add6fdc3-a866.json`):

- **One webhook push = One complete transcript session**
- **Session Duration**: Typically under 1 hour (example: 42:33 = 42 minutes 33 seconds)
- **Transcript Structure**: JSON array of sentence objects with timestamps

### **Actual Fireflies Transcript Structure**

```json
[
  {
    "sentence": "And welcome to where is the trade?",
    "startTime": "00:05",
    "endTime": "00:07", 
    "speaker_name": "speaker 2",
    "speaker_id": 1
  },
  {
    "sentence": "It is Friday, June 6th, 2025.",
    "startTime": "00:07",
    "endTime": "00:10",
    "speaker_name": "speaker 2", 
    "speaker_id": 1
  }
  // ... continues for entire session
]
```

### **Timestamp Format Analysis**

#### **✅ Fireflies Uses MM:SS Format**
- **Format**: `"MM:SS"` (e.g., "00:05", "01:23", "42:33")
- **Fields**: `startTime` and `endTime` for each sentence
- **Duration Calculation**: Find the maximum `endTime` value across all sentences

#### **Session Duration Examples**
- **Example Session**: 00:00 → 42:33 = **42 minutes 33 seconds**
- **Maximum Expected**: **1 hour** (as confirmed by user)

## Enhanced Timestamp Detection Implementation

### **1. Fireflies JSON Format Support**
```python
# Detects and parses Fireflies JSON structure
if transcript_text.strip().startswith('[') and transcript_text.strip().endswith(']'):
    transcript_data = json.loads(transcript_text)
    for entry in transcript_data:
        start_time = entry.get('startTime', '')  # "00:05"
        end_time = entry.get('endTime', '')      # "00:07"
        # Convert to seconds and find maximum
```

### **2. Traditional Format Fallback**
- MM:SS, HH:MM:SS, [MM:SS], XmYs, Xs patterns
- Used for non-Fireflies transcript sources

### **3. No-Timestamp Handling**
- **Environment Variable**: `ALLOW_NO_TIMESTAMPS=true`
- **Default Duration**: `DEFAULT_TRANSCRIPT_DURATION=3600` (1 hour)
- **Use Case**: Financial commentary without speaker timestamps

## Configuration Updates

### **Updated Environment Variables**
```bash
# Timestamp Processing Configuration
ALLOW_NO_TIMESTAMPS=true
# Default duration for sessions without timestamps (3600 seconds = 1 hour max session length)
DEFAULT_TRANSCRIPT_DURATION=3600
```

### **Why 3600 Seconds (1 Hour)?**
- **User Confirmation**: "sessions are maximum 1 hour"
- **Safety Margin**: Covers the longest possible Fireflies session
- **Anti-Hallucination**: Prevents AI from generating timestamps beyond realistic session length

## Anti-Hallucination Validation Impact

### **How Duration is Used**
1. **Extract session duration** from Fireflies JSON timestamps
2. **Validate AI-generated timestamps** don't exceed actual session length
3. **Prevent hallucination** of content beyond the actual recording

### **Example Validation**
```python
# Session duration: 42:33 (2553 seconds)
# AI generates timestamp: "45:00" (2700 seconds)
# Validation: FAIL - exceeds actual session duration
# Result: Confidence score reduced, flagged as potential hallucination
```

## Benefits of Enhanced Implementation

### **✅ Accurate Duration Detection**
- **Fireflies JSON**: Precise duration from actual timestamps
- **Traditional Formats**: Backward compatibility maintained
- **No-Timestamp Fallback**: Explicit handling with realistic defaults

### **✅ Improved Anti-Hallucination**
- **Realistic Boundaries**: 1-hour maximum prevents unrealistic timestamp generation
- **Session-Specific**: Each transcript gets its actual duration for validation
- **Explicit Failures**: No fallbacks that mask real issues

### **✅ Production Ready**
- **Multiple Format Support**: Handles various transcript sources
- **Comprehensive Logging**: Detailed debugging information
- **Environment Configuration**: Flexible deployment options

## Testing Recommendations

### **Test Cases to Verify**
1. **Fireflies JSON**: Process actual Fireflies transcript with timestamps
2. **Traditional Format**: Test with MM:SS format transcripts
3. **No Timestamps**: Verify financial commentary processing
4. **Edge Cases**: Empty transcripts, malformed JSON, invalid timestamps

### **Validation Checks**
- Duration extraction accuracy
- Anti-hallucination boundary enforcement
- Error handling for malformed data
- Environment variable configuration 