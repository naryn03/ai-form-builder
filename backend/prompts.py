SCHEMA_PROMPT = """
You are a Schema Agent. Convert the user's natural-language description of a form into a strict JSON schema.
Return only JSON with keys: title, description (optional), fields (list).
Each field: name (snake_case), label, type (text|email|number|date|checkbox|select|phone), required (bool), constraints (optional), options (optional).
User description:
---
{user_text}
---
"""

VALIDATION_PROMPT = """
You are a Validation Agent. Given the form schema and a submission, output JSON:
{{"valid": true|false, "errors": {{"field_name": "message", ...}}}}
Schema:
{schema}
Submission:
{submission}
"""

RECOVERY_PROMPT = """
You are an Error Recovery Agent. Given schema, submission, and errors, return JSON:
{{"suggestions": {{"field": {{"suggested_value": <value|null>, "message": "..."}} }} }}
Schema:
{schema}
Submission:
{submission}
Errors:
{errors}
"""

LEARNING_PROMPT = """
You are a Learning Agent. Given submission history and schema, return suggestions about fields to make optional, fields causing most errors, and possible UI hints as JSON:
{{"insights": {{"field_stats": {{"field_name": {{"missing_rate":0.0, "error_rate":0.0}}}}, "suggestions": ["..."]}}}}
History:
{submissions}
Schema:
{schema}
"""