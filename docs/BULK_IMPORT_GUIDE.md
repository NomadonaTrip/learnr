# Bulk Question Import Guide

This guide explains how to import multiple questions at once into the LearnR platform using the admin bulk import endpoint.

## Table of Contents

- [Overview](#overview)
- [API Endpoint](#api-endpoint)
- [JSON Structure](#json-structure)
- [Field Specifications](#field-specifications)
- [Validation Rules](#validation-rules)
- [Examples](#examples)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

The bulk import feature allows administrators to import between 1 and 500 questions at once. Questions are validated individually, and the import uses transaction savepoints to allow partial success - some questions can import successfully even if others fail.

**Key Features:**
- Import 1-500 questions per request
- Individual question validation with detailed error reporting
- Partial success support (some questions succeed, others fail)
- Automatic knowledge area and domain validation
- Support for multiple-choice and true/false questions
- Configurable difficulty levels (0.0 to 1.0)

---

## API Endpoint

```http
POST /v1/admin/courses/{course_id}/questions/bulk
Content-Type: application/json
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "course_id": "uuid",
  "questions_imported": 150,
  "questions_failed": 2,
  "validation_summary": {
    "total_submitted": 152,
    "successful": 150,
    "failed": 2,
    "errors": [
      {
        "question_index": 45,
        "error": "Knowledge area 'INVALID_KA' not found"
      },
      {
        "question_index": 89,
        "error": "Exactly one answer must be correct, got 2"
      }
    ]
  }
}
```

---

## JSON Structure

### Top-Level Structure

```json
{
  "questions": [
    {
      "ka_code": "string",
      "domain_code": "string | null",
      "question_text": "string",
      "question_type": "multiple_choice | true_false",
      "difficulty": 0.5,
      "source": "vendor | generated | custom",
      "answer_choices": [
        {
          "choice_text": "string",
          "is_correct": true,
          "choice_order": 1,
          "explanation": "string | null"
        }
      ]
    }
  ]
}
```

### Minimum Valid Request

```json
{
  "questions": [
    {
      "ka_code": "NEEDS_ASSESSMENT",
      "question_text": "What is the primary purpose of needs assessment?",
      "question_type": "multiple_choice",
      "difficulty": 0.5,
      "source": "vendor",
      "answer_choices": [
        {
          "choice_text": "To identify gaps between current and desired states",
          "is_correct": true,
          "choice_order": 1
        },
        {
          "choice_text": "To create a project schedule",
          "is_correct": false,
          "choice_order": 2
        }
      ]
    }
  ]
}
```

---

## Field Specifications

### Question Fields

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `ka_code` | string | Yes | Knowledge area code | Max 20 chars, must exist in course |
| `domain_code` | string | No | Optional domain code | Max 20 chars, must exist in KA if provided |
| `question_text` | string | Yes | The question content | 10-5000 chars |
| `question_type` | string | Yes | Type of question | `"multiple_choice"` or `"true_false"` |
| `difficulty` | number | Yes | Question difficulty | 0.0 to 1.0 (0=easiest, 1=hardest) |
| `source` | string | Yes | Question origin | `"vendor"`, `"generated"`, or `"custom"` |
| `answer_choices` | array | Yes | Answer options | 2-6 choices |

### Answer Choice Fields

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `choice_text` | string | Yes | Answer text | 1-1000 chars |
| `is_correct` | boolean | Yes | Whether this is the correct answer | Exactly one choice must be true |
| `choice_order` | integer | Yes | Display order | 1-6, unique per question |
| `explanation` | string | No | Why this answer is correct/incorrect | Max 1000 chars |

---

## Validation Rules

### Question-Level Validation

1. **Knowledge Area**: Must exist in the target course
2. **Domain**: If provided, must exist within the specified knowledge area
3. **Question Text**: Must be 10-5000 characters
4. **Difficulty**: Must be between 0.0 and 1.0
5. **Question Type**: Must be `"multiple_choice"` or `"true_false"`
6. **Source**: Must be `"vendor"`, `"generated"`, or `"custom"`

### Answer Choice Validation

1. **Minimum Choices**: At least 2 answer choices required
2. **Maximum Choices**: No more than 6 answer choices
3. **Exactly One Correct**: Exactly one answer must have `is_correct: true`
4. **Choice Order**: Must be integers between 1 and 6
5. **Unique Order**: Each choice in a question must have unique `choice_order`

### Request-Level Validation

1. **Minimum Questions**: At least 1 question required
2. **Maximum Questions**: No more than 500 questions per request
3. **JSON Format**: Must be valid JSON structure

---

## Examples

### Example 1: Single Multiple-Choice Question

```json
{
  "questions": [
    {
      "ka_code": "BUSINESS_ANALYSIS_PLANNING",
      "domain_code": "STAKEHOLDER_ENGAGEMENT",
      "question_text": "Which technique is most effective for identifying stakeholder communication preferences?",
      "question_type": "multiple_choice",
      "difficulty": 0.6,
      "source": "vendor",
      "answer_choices": [
        {
          "choice_text": "Stakeholder interviews",
          "is_correct": true,
          "choice_order": 1,
          "explanation": "Direct interviews allow you to ask stakeholders about their preferred communication methods, frequency, and formats."
        },
        {
          "choice_text": "Document analysis",
          "is_correct": false,
          "choice_order": 2,
          "explanation": "Document analysis helps understand existing processes but doesn't reveal personal communication preferences."
        },
        {
          "choice_text": "SWOT analysis",
          "is_correct": false,
          "choice_order": 3,
          "explanation": "SWOT is for strategic planning, not stakeholder communication analysis."
        },
        {
          "choice_text": "Use case modeling",
          "is_correct": false,
          "choice_order": 4,
          "explanation": "Use cases model system behavior, not stakeholder preferences."
        }
      ]
    }
  ]
}
```

### Example 2: True/False Question

```json
{
  "questions": [
    {
      "ka_code": "REQUIREMENTS_LIFECYCLE",
      "question_text": "Requirements should never be changed once they are approved and baselined.",
      "question_type": "true_false",
      "difficulty": 0.3,
      "source": "custom",
      "answer_choices": [
        {
          "choice_text": "True",
          "is_correct": false,
          "choice_order": 1,
          "explanation": "Requirements can and should be changed when business needs evolve, but changes must go through formal change control."
        },
        {
          "choice_text": "False",
          "is_correct": true,
          "choice_order": 2,
          "explanation": "Correct. Requirements can change after baseline through a controlled change management process."
        }
      ]
    }
  ]
}
```

### Example 3: Multiple Questions (Batch Import)

```json
{
  "questions": [
    {
      "ka_code": "ELICITATION",
      "question_text": "What is the primary advantage of using workshops for requirements elicitation?",
      "question_type": "multiple_choice",
      "difficulty": 0.5,
      "source": "vendor",
      "answer_choices": [
        {
          "choice_text": "Facilitates collaboration and consensus building among stakeholders",
          "is_correct": true,
          "choice_order": 1
        },
        {
          "choice_text": "Reduces the time required for analysis",
          "is_correct": false,
          "choice_order": 2
        },
        {
          "choice_text": "Eliminates the need for documentation",
          "is_correct": false,
          "choice_order": 3
        }
      ]
    },
    {
      "ka_code": "ELICITATION",
      "domain_code": "ELICITATION_TECHNIQUES",
      "question_text": "Which elicitation technique is best suited for understanding complex business processes?",
      "question_type": "multiple_choice",
      "difficulty": 0.7,
      "source": "vendor",
      "answer_choices": [
        {
          "choice_text": "Process modeling and observation",
          "is_correct": true,
          "choice_order": 1,
          "explanation": "Combining process modeling with observation provides comprehensive understanding of complex workflows."
        },
        {
          "choice_text": "Survey",
          "is_correct": false,
          "choice_order": 2,
          "explanation": "Surveys are better for gathering quantitative data from many respondents, not complex process details."
        },
        {
          "choice_text": "Brainstorming",
          "is_correct": false,
          "choice_order": 3,
          "explanation": "Brainstorming generates ideas but doesn't map existing processes."
        }
      ]
    },
    {
      "ka_code": "REQUIREMENTS_ANALYSIS",
      "question_text": "The primary goal of requirements analysis is to identify gaps and conflicts in requirements.",
      "question_type": "true_false",
      "difficulty": 0.4,
      "source": "custom",
      "answer_choices": [
        {
          "choice_text": "True",
          "is_correct": true,
          "choice_order": 1,
          "explanation": "Requirements analysis includes identifying gaps, conflicts, and ambiguities to ensure complete, consistent requirements."
        },
        {
          "choice_text": "False",
          "is_correct": false,
          "choice_order": 2
        }
      ]
    }
  ]
}
```

### Example 4: AI-Generated Questions

```json
{
  "questions": [
    {
      "ka_code": "SOLUTION_EVALUATION",
      "question_text": "Which metric is most appropriate for measuring solution performance after deployment?",
      "question_type": "multiple_choice",
      "difficulty": 0.6,
      "source": "generated",
      "answer_choices": [
        {
          "choice_text": "Key Performance Indicators (KPIs) aligned with business objectives",
          "is_correct": true,
          "choice_order": 1
        },
        {
          "choice_text": "Lines of code written",
          "is_correct": false,
          "choice_order": 2
        },
        {
          "choice_text": "Number of features implemented",
          "is_correct": false,
          "choice_order": 3
        },
        {
          "choice_text": "Project budget variance",
          "is_correct": false,
          "choice_order": 4
        }
      ]
    }
  ]
}
```

---

## Error Handling

### Common Validation Errors

#### 1. Invalid Knowledge Area Code

```json
{
  "validation_summary": {
    "errors": [
      {
        "question_index": 0,
        "error": "Knowledge area 'INVALID_KA' not found in course"
      }
    ]
  }
}
```

**Solution**: Verify the knowledge area code exists in the target course. Use `GET /v1/admin/courses/{course_id}` to list valid KA codes.

#### 2. Multiple Correct Answers

```json
{
  "validation_summary": {
    "errors": [
      {
        "question_index": 5,
        "error": "Exactly one answer must be correct, got 2"
      }
    ]
  }
}
```

**Solution**: Ensure exactly one answer choice has `is_correct: true` for each question.

#### 3. Question Text Too Short

```json
{
  "validation_summary": {
    "errors": [
      {
        "question_index": 12,
        "error": "question_text: String should have at least 10 characters"
      }
    ]
  }
}
```

**Solution**: Question text must be at least 10 characters. Expand the question with more context.

#### 4. Invalid Difficulty Range

```json
{
  "validation_summary": {
    "errors": [
      {
        "question_index": 8,
        "error": "difficulty: Input should be less than or equal to 1"
      }
    ]
  }
}
```

**Solution**: Difficulty must be between 0.0 and 1.0. Common values:
- 0.0-0.3: Easy
- 0.4-0.6: Medium
- 0.7-1.0: Hard

#### 5. Invalid Question Type

```json
{
  "validation_summary": {
    "errors": [
      {
        "question_index": 3,
        "error": "question_type must be 'multiple_choice' or 'true_false'"
      }
    ]
  }
}
```

**Solution**: Use only `"multiple_choice"` or `"true_false"` (case-sensitive).

#### 6. Invalid Source

```json
{
  "validation_summary": {
    "errors": [
      {
        "question_index": 10,
        "error": "source must be 'vendor', 'generated', or 'custom'"
      }
    ]
  }
}
```

**Solution**: Use only `"vendor"`, `"generated"`, or `"custom"` (case-sensitive).

---

## Best Practices

### 1. Batch Size Optimization

- **Recommended**: 50-100 questions per batch for optimal performance
- **Minimum**: 1 question (for testing individual questions)
- **Maximum**: 500 questions (hard limit)

### 2. Question Quality

- Write clear, unambiguous question text (10-200 characters is ideal)
- Provide explanations for correct and incorrect answers
- Use consistent difficulty calibration across your question bank
- Test questions with sample users before bulk import

### 3. Difficulty Calibration

| Difficulty | Description | IRT Theta | Expected Pass Rate |
|------------|-------------|-----------|-------------------|
| 0.0-0.2 | Very Easy | -2.0 to -1.0 | 90%+ |
| 0.3-0.4 | Easy | -0.9 to -0.3 | 70-89% |
| 0.5-0.6 | Medium | -0.2 to 0.2 | 50-69% |
| 0.7-0.8 | Hard | 0.3 to 0.9 | 30-49% |
| 0.9-1.0 | Very Hard | 1.0 to 2.0 | <30% |

### 4. Knowledge Area Distribution

Distribute questions proportionally to knowledge area weights:

```python
# Example for CBAP (6 knowledge areas)
total_questions = 300

ka_distribution = {
    "BUSINESS_ANALYSIS_PLANNING": 45,      # 15% weight
    "ELICITATION": 60,                     # 20% weight
    "REQUIREMENTS_LIFECYCLE": 75,          # 25% weight
    "STRATEGY_ANALYSIS": 30,               # 10% weight
    "REQUIREMENTS_ANALYSIS": 60,           # 20% weight
    "SOLUTION_EVALUATION": 30              # 10% weight
}
```

### 5. Answer Choice Guidelines

- **Multiple-Choice**: Use 3-5 answer choices (4 is optimal)
- **Distractors**: Make incorrect answers plausible but clearly wrong
- **Length**: Keep answer choices roughly equal length
- **Position**: Randomize correct answer position (don't always use choice 1)

### 6. Error Recovery Strategy

```python
# Pseudo-code for handling partial failures
response = bulk_import(questions)

if response.questions_failed > 0:
    # Extract failed questions
    failed_indices = [err.question_index for err in response.validation_summary.errors]
    failed_questions = [questions[i] for i in failed_indices]

    # Fix issues and retry
    fixed_questions = fix_validation_errors(failed_questions)
    retry_response = bulk_import(fixed_questions)
```

### 7. Pre-Import Validation Checklist

Before importing, verify:
- [ ] All KA codes exist in the target course
- [ ] Domain codes (if used) exist in their respective KAs
- [ ] Each question has exactly one correct answer
- [ ] Difficulty values are between 0.0 and 1.0
- [ ] Question types are `"multiple_choice"` or `"true_false"`
- [ ] Source values are `"vendor"`, `"generated"`, or `"custom"`
- [ ] Answer choices have unique `choice_order` values (1-6)
- [ ] Question text is at least 10 characters

---

## Troubleshooting

### Issue: "Course not found"

**Cause**: Invalid `course_id` in URL or course status is not `'draft'` or `'active'`.

**Solution**:
```bash
# List all courses to verify course_id
GET /v1/admin/courses

# Check course status
GET /v1/admin/courses/{course_id}
```

### Issue: "Exactly one answer must be correct"

**Cause**: Multiple answers have `is_correct: true` or no answers are marked correct.

**Solution**: Verify each question has exactly one answer with `is_correct: true`:
```json
{
  "answer_choices": [
    {"choice_text": "Correct answer", "is_correct": true, "choice_order": 1},
    {"choice_text": "Wrong answer 1", "is_correct": false, "choice_order": 2},
    {"choice_text": "Wrong answer 2", "is_correct": false, "choice_order": 3}
  ]
}
```

### Issue: "Knowledge area 'XXX' not found"

**Cause**: KA code doesn't exist in the target course or is misspelled.

**Solution**:
```bash
# Get valid KA codes for the course
GET /v1/admin/courses/{course_id}/knowledge-areas

# Common CBAP KA codes:
# - BUSINESS_ANALYSIS_PLANNING
# - ELICITATION
# - REQUIREMENTS_LIFECYCLE
# - STRATEGY_ANALYSIS
# - REQUIREMENTS_ANALYSIS
# - SOLUTION_EVALUATION
```

### Issue: Timeout on large imports

**Cause**: Importing 500 questions can take 30+ seconds.

**Solution**: Split large imports into smaller batches:
```python
# Split into batches of 100
batch_size = 100
for i in range(0, len(all_questions), batch_size):
    batch = all_questions[i:i+batch_size]
    response = bulk_import(batch)
    print(f"Batch {i//batch_size + 1}: {response.questions_imported} imported")
```

### Issue: "Duplicate choice_order values"

**Cause**: Multiple answer choices have the same `choice_order` value.

**Solution**: Ensure each answer choice has a unique order:
```json
{
  "answer_choices": [
    {"choice_text": "Answer 1", "is_correct": true, "choice_order": 1},
    {"choice_text": "Answer 2", "is_correct": false, "choice_order": 2},  // Must be unique
    {"choice_text": "Answer 3", "is_correct": false, "choice_order": 3}   // Must be unique
  ]
}
```

---

## Appendix: Complete CBAP Example

Here's a complete example importing 5 questions across different CBAP knowledge areas:

```json
{
  "questions": [
    {
      "ka_code": "BUSINESS_ANALYSIS_PLANNING",
      "domain_code": "STAKEHOLDER_ENGAGEMENT",
      "question_text": "What is the primary purpose of the stakeholder engagement approach?",
      "question_type": "multiple_choice",
      "difficulty": 0.5,
      "source": "vendor",
      "answer_choices": [
        {
          "choice_text": "To define how stakeholders will be engaged throughout the initiative",
          "is_correct": true,
          "choice_order": 1,
          "explanation": "The stakeholder engagement approach outlines methods, timing, and frequency of stakeholder interactions."
        },
        {
          "choice_text": "To create a project budget",
          "is_correct": false,
          "choice_order": 2,
          "explanation": "Budget creation is part of project management, not stakeholder engagement planning."
        },
        {
          "choice_text": "To develop technical requirements",
          "is_correct": false,
          "choice_order": 3,
          "explanation": "Technical requirements are developed during requirements analysis, not engagement planning."
        }
      ]
    },
    {
      "ka_code": "ELICITATION",
      "question_text": "Brainstorming is always the most effective elicitation technique for gathering requirements.",
      "question_type": "true_false",
      "difficulty": 0.3,
      "source": "custom",
      "answer_choices": [
        {
          "choice_text": "True",
          "is_correct": false,
          "choice_order": 1,
          "explanation": "Different techniques are effective in different contexts. Brainstorming is good for generating ideas but not for all requirement types."
        },
        {
          "choice_text": "False",
          "is_correct": true,
          "choice_order": 2,
          "explanation": "Correct. The most effective technique depends on the context, stakeholders, and type of requirements being elicited."
        }
      ]
    },
    {
      "ka_code": "REQUIREMENTS_LIFECYCLE",
      "domain_code": "TRACE_REQUIREMENTS",
      "question_text": "What is the primary benefit of maintaining requirements traceability?",
      "question_type": "multiple_choice",
      "difficulty": 0.6,
      "source": "vendor",
      "answer_choices": [
        {
          "choice_text": "Enables impact analysis when requirements change",
          "is_correct": true,
          "choice_order": 1,
          "explanation": "Traceability links help identify which designs, tests, and code are affected by requirement changes."
        },
        {
          "choice_text": "Reduces project costs",
          "is_correct": false,
          "choice_order": 2,
          "explanation": "While traceability can reduce rework costs, cost reduction is not its primary purpose."
        },
        {
          "choice_text": "Eliminates the need for testing",
          "is_correct": false,
          "choice_order": 3,
          "explanation": "Traceability supports testing by linking requirements to test cases, but doesn't eliminate testing."
        },
        {
          "choice_text": "Automates requirement validation",
          "is_correct": false,
          "choice_order": 4,
          "explanation": "Traceability is a manual activity; it doesn't automate validation."
        }
      ]
    },
    {
      "ka_code": "STRATEGY_ANALYSIS",
      "question_text": "Which technique is most appropriate for analyzing the current state of an organization?",
      "question_type": "multiple_choice",
      "difficulty": 0.7,
      "source": "vendor",
      "answer_choices": [
        {
          "choice_text": "Process modeling and capability analysis",
          "is_correct": true,
          "choice_order": 1,
          "explanation": "These techniques provide comprehensive understanding of current processes and organizational capabilities."
        },
        {
          "choice_text": "Prototyping",
          "is_correct": false,
          "choice_order": 2,
          "explanation": "Prototyping is for exploring future solutions, not analyzing current state."
        },
        {
          "choice_text": "User story mapping",
          "is_correct": false,
          "choice_order": 3,
          "explanation": "User stories describe desired functionality, not current state analysis."
        }
      ]
    },
    {
      "ka_code": "SOLUTION_EVALUATION",
      "domain_code": "MEASURE_SOLUTION_PERFORMANCE",
      "question_text": "Solution performance metrics should be defined after the solution is deployed to see what can be measured.",
      "question_type": "true_false",
      "difficulty": 0.4,
      "source": "custom",
      "answer_choices": [
        {
          "choice_text": "True",
          "is_correct": false,
          "choice_order": 1,
          "explanation": "Metrics should be defined during requirements analysis to ensure the solution can support measurement."
        },
        {
          "choice_text": "False",
          "is_correct": true,
          "choice_order": 2,
          "explanation": "Correct. Performance metrics must be defined early so the solution is designed to capture required data."
        }
      ]
    }
  ]
}
```

---

## Quick Reference

### Allowed Values

| Field | Allowed Values |
|-------|---------------|
| `question_type` | `"multiple_choice"`, `"true_false"` |
| `source` | `"vendor"`, `"generated"`, `"custom"` |
| `difficulty` | `0.0` to `1.0` (decimals allowed) |
| `choice_order` | `1` to `6` (integers only) |

### Field Lengths

| Field | Minimum | Maximum |
|-------|---------|---------|
| `question_text` | 10 chars | 5,000 chars |
| `choice_text` | 1 char | 1,000 chars |
| `explanation` | 0 chars | 1,000 chars |
| `ka_code` | 1 char | 20 chars |
| `domain_code` | 1 char | 20 chars |

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 201 | Questions imported successfully |
| 400 | Validation error (check `validation_summary.errors`) |
| 401 | Not authenticated |
| 403 | Not authorized (requires admin role) |
| 404 | Course not found |
| 422 | Unprocessable entity (invalid JSON structure) |

---

## Support

For additional help:
- **API Documentation**: `/docs` (Swagger UI)
- **Admin Dashboard**: View imported questions and statistics
- **Error Logs**: Check `validation_summary.errors` for detailed error messages

---

**Version**: 1.0
**Last Updated**: 2025-01-09
**Endpoint**: `POST /v1/admin/courses/{course_id}/questions/bulk`
