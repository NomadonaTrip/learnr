# Bulk Import Quick Reference Card

**Endpoint**: `POST /v1/admin/courses/{course_id}/questions/bulk`

## Minimal Request Template

```json
{
  "questions": [
    {
      "ka_code": "YOUR_KA_CODE",
      "question_text": "Your question here (10-5000 chars)",
      "question_type": "multiple_choice",
      "difficulty": 0.5,
      "source": "vendor",
      "answer_choices": [
        {
          "choice_text": "Correct answer",
          "is_correct": true,
          "choice_order": 1
        },
        {
          "choice_text": "Wrong answer",
          "is_correct": false,
          "choice_order": 2
        }
      ]
    }
  ]
}
```

## Field Constraints

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `ka_code` | string | ✓ | Max 20 chars, must exist |
| `domain_code` | string | ✗ | Max 20 chars, must exist in KA |
| `question_text` | string | ✓ | 10-5000 chars |
| `question_type` | string | ✓ | `"multiple_choice"` or `"true_false"` |
| `difficulty` | number | ✓ | 0.0 to 1.0 |
| `source` | string | ✓ | `"vendor"`, `"generated"`, `"custom"` |
| `answer_choices` | array | ✓ | 2-6 choices |
| `choice_text` | string | ✓ | 1-1000 chars |
| `is_correct` | boolean | ✓ | Exactly ONE must be true |
| `choice_order` | integer | ✓ | 1-6, unique per question |
| `explanation` | string | ✗ | Max 1000 chars |

## Difficulty Scale

| Value | Level | Pass Rate | When to Use |
|-------|-------|-----------|-------------|
| 0.0-0.3 | Easy | 90%+ | Foundational concepts |
| 0.4-0.6 | Medium | 50-70% | Standard questions |
| 0.7-1.0 | Hard | <30% | Advanced/tricky concepts |

## Validation Checklist

Before importing, verify:

- [ ] KA codes exist in target course
- [ ] Question text ≥ 10 characters
- [ ] Exactly ONE answer marked correct per question
- [ ] Difficulty between 0.0 and 1.0
- [ ] Question type is `"multiple_choice"` or `"true_false"`
- [ ] Source is `"vendor"`, `"generated"`, or `"custom"`
- [ ] Choice order values are unique (1-6)
- [ ] Valid JSON format

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Knowledge area 'XXX' not found" | Invalid KA code | Verify KA exists in course |
| "Exactly one answer must be correct" | Multiple/no correct answers | Set ONE `is_correct: true` |
| "String should have at least 10 characters" | Question too short | Expand question text |
| "Input should be less than or equal to 1" | difficulty > 1.0 | Use 0.0-1.0 range |
| "String should have at most 20 characters" | KA/domain code too long | Shorten to ≤ 20 chars |

## Limits

- **Min questions per request**: 1
- **Max questions per request**: 500
- **Recommended batch size**: 50-100 questions
- **Min answer choices**: 2
- **Max answer choices**: 6

## Pre-Import Validation

```bash
# Validate JSON before importing
python scripts/validate_bulk_import.py your_questions.json

# Show statistics only
python scripts/validate_bulk_import.py your_questions.json --stats-only
```

## Sample Files

Templates available in `docs/samples/`:
- `bulk_import_minimal.json` - Basic structure
- `bulk_import_with_explanations.json` - With explanations
- `bulk_import_true_false.json` - True/False examples
- `bulk_import_batch.json` - Multiple questions

## Response Format

```json
{
  "course_id": "uuid",
  "questions_imported": 48,
  "questions_failed": 2,
  "validation_summary": {
    "total_submitted": 50,
    "successful": 48,
    "failed": 2,
    "errors": [
      {
        "question_index": 12,
        "error": "Knowledge area 'INVALID_KA' not found"
      }
    ]
  }
}
```

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 201 | Success - questions imported |
| 400 | Validation error |
| 401 | Not authenticated |
| 403 | Not authorized (need admin role) |
| 404 | Course not found |

## Tips

1. **Start Small**: Test with 1-5 questions first
2. **Use Templates**: Copy from `docs/samples/`
3. **Validate First**: Always run validation script
4. **Batch Wisely**: 50-100 questions per batch optimal
5. **Distribute**: Spread questions across all KAs
6. **Add Explanations**: Improves learning outcomes
7. **Review Errors**: Check `validation_summary.errors`

## Documentation

- Full Guide: `docs/BULK_IMPORT_GUIDE.md`
- API Docs: `/docs` (Swagger UI)
- Scripts: `scripts/README.md`

---

**Version**: 1.0 | **Updated**: 2025-01-09
