# TDD Addendum - Content Quality Evaluation System
# Adaptive CBAP Learning Platform

**Version:** 1.1 (Addendum to v1.0)  
**Date:** October 24, 2025  
**Decision Reference:** #76  
**Status:** APPROVED - CRITICAL FOR MVP

---

## Overview

This addendum adds a comprehensive content quality evaluation system to ensure reading recommendations are both **relevant** (matching user needs) and **accurate** (factually correct).

**Problem Solved:**
- ✅ Validates content accuracy before showing to users
- ✅ Measures content effectiveness (does it improve competency?)
- ✅ Collects user feedback on helpfulness
- ✅ Flags low-quality content for review
- ✅ Continuous quality improvement loop

---

## 1. DATABASE SCHEMA ADDITIONS

### 1.1 Update: content_chunks table

**Add Quality Control Fields:**

```sql
ALTER TABLE content_chunks 
ADD COLUMN expert_reviewed BOOLEAN DEFAULT false,
ADD COLUMN review_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN source_verified BOOLEAN DEFAULT false,
ADD COLUMN is_active BOOLEAN DEFAULT false,
ADD CONSTRAINT chk_review_status 
    CHECK (review_status IN ('pending', 'approved', 'flagged', 'rejected'));

-- Index for filtering active content
CREATE INDEX idx_chunks_active ON content_chunks(is_active, review_status);

-- Comment updates
COMMENT ON COLUMN content_chunks.expert_reviewed IS 'Has content been reviewed by subject matter expert';
COMMENT ON COLUMN content_chunks.review_status IS 'Approval workflow status';
COMMENT ON COLUMN content_chunks.source_verified IS 'Has source reference been verified';
COMMENT ON COLUMN content_chunks.is_active IS 'Visible to learners (only if approved)';
```

### 1.2 New Table: content_feedback

**User feedback on content helpfulness:**

```sql
CREATE TABLE content_feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES content_chunks(chunk_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Feedback data
    was_helpful BOOLEAN NOT NULL,
    feedback_text TEXT,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(chunk_id, user_id)  -- One feedback per user per chunk
);

CREATE INDEX idx_feedback_chunk ON content_feedback(chunk_id);
CREATE INDEX idx_feedback_helpful ON content_feedback(was_helpful);
CREATE INDEX idx_feedback_user ON content_feedback(user_id);

-- Aggregate view for helpfulness score
CREATE VIEW content_helpfulness AS
SELECT 
    chunk_id,
    COUNT(*) as total_feedback,
    SUM(CASE WHEN was_helpful THEN 1 ELSE 0 END) as helpful_count,
    ROUND(
        100.0 * SUM(CASE WHEN was_helpful THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) as helpfulness_percentage
FROM content_feedback
GROUP BY chunk_id;
```

### 1.3 New Table: content_efficacy

**Measures whether content improves user competency:**

```sql
CREATE TABLE content_efficacy (
    efficacy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES content_chunks(chunk_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    ka_id UUID NOT NULL REFERENCES knowledge_areas(ka_id) ON DELETE CASCADE,
    
    -- Efficacy measurement
    read_at TIMESTAMP NOT NULL,
    competency_before DECIMAL(5,2) NOT NULL,  -- User's competency when they read
    competency_after DECIMAL(5,2),  -- NULL until user practices (measured 24hr later)
    measured_at TIMESTAMP,
    
    -- Computed fields
    improved BOOLEAN,  -- TRUE if competency_after > competency_before
    improvement_amount DECIMAL(5,2),  -- competency_after - competency_before
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_competency_range 
        CHECK (competency_before >= 0 AND competency_before <= 1 
               AND (competency_after IS NULL OR (competency_after >= 0 AND competency_after <= 1)))
);

CREATE INDEX idx_efficacy_chunk ON content_efficacy(chunk_id);
CREATE INDEX idx_efficacy_user ON content_efficacy(user_id);
CREATE INDEX idx_efficacy_improved ON content_efficacy(improved) WHERE improved IS NOT NULL;
CREATE INDEX idx_efficacy_pending ON content_efficacy(read_at) WHERE competency_after IS NULL;

-- Aggregate view for efficacy rate
CREATE VIEW content_efficacy_stats AS
SELECT 
    chunk_id,
    COUNT(*) as total_reads,
    SUM(CASE WHEN improved = true THEN 1 ELSE 0 END) as improved_count,
    ROUND(
        100.0 * SUM(CASE WHEN improved = true THEN 1 ELSE 0 END) / 
        NULLIF(SUM(CASE WHEN improved IS NOT NULL THEN 1 ELSE 0 END), 0),
        2
    ) as efficacy_percentage,
    ROUND(AVG(improvement_amount), 3) as avg_improvement
FROM content_efficacy
GROUP BY chunk_id;
```

---

## 2. DATA MODELS ADDITIONS

### 2.1 Update: ContentChunk Model

```python
# app/models/content.py

class ContentChunk(Base):
    """
    Content chunks with quality control.
    """
    __tablename__ = "content_chunks"
    
    # ... existing fields ...
    
    # Quality control (NEW)
    expert_reviewed = Column(Boolean, nullable=False, default=False)
    review_status = Column(String(20), nullable=False, default='pending')
    source_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=False)
    
    # Relationships (NEW)
    feedback = relationship("ContentFeedback", back_populates="chunk", cascade="all, delete-orphan")
    efficacy_records = relationship("ContentEfficacy", back_populates="chunk", cascade="all, delete-orphan")
    
    # Check constraint
    __table_args__ = (
        CheckConstraint("review_status IN ('pending', 'approved', 'flagged', 'rejected')", 
                       name='chk_review_status'),
    )
    
    @property
    def helpfulness_score(self) -> Optional[float]:
        """Calculate helpfulness percentage from feedback."""
        if not self.feedback:
            return None
        total = len(self.feedback)
        helpful = sum(1 for f in self.feedback if f.was_helpful)
        return round((helpful / total) * 100, 2) if total > 0 else None
    
    @property
    def efficacy_rate(self) -> Optional[float]:
        """Calculate efficacy percentage."""
        measured = [e for e in self.efficacy_records if e.improved is not None]
        if not measured:
            return None
        improved = sum(1 for e in measured if e.improved)
        return round((improved / len(measured)) * 100, 2)
```

### 2.2 New Model: ContentFeedback

```python
# app/models/content.py

class ContentFeedback(Base):
    """
    User feedback on content helpfulness.
    """
    __tablename__ = "content_feedback"
    
    # Primary Key
    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    chunk_id = Column(UUID(as_uuid=True), ForeignKey('content_chunks.chunk_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    
    # Feedback
    was_helpful = Column(Boolean, nullable=False)
    feedback_text = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    chunk = relationship("ContentChunk", back_populates="feedback")
    user = relationship("User")
    
    def __repr__(self):
        return f"<ContentFeedback {self.feedback_id} - {'Helpful' if self.was_helpful else 'Not Helpful'}>"
```

### 2.3 New Model: ContentEfficacy

```python
# app/models/content.py

class ContentEfficacy(Base):
    """
    Measures whether content improves user competency.
    """
    __tablename__ = "content_efficacy"
    
    # Primary Key
    efficacy_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    chunk_id = Column(UUID(as_uuid=True), ForeignKey('content_chunks.chunk_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    ka_id = Column(UUID(as_uuid=True), ForeignKey('knowledge_areas.ka_id', ondelete='CASCADE'), nullable=False)
    
    # Efficacy measurement
    read_at = Column(DateTime, nullable=False)
    competency_before = Column(DECIMAL(5, 2), nullable=False)
    competency_after = Column(DECIMAL(5, 2), nullable=True)
    measured_at = Column(DateTime, nullable=True)
    
    # Computed
    improved = Column(Boolean, nullable=True)
    improvement_amount = Column(DECIMAL(5, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    chunk = relationship("ContentChunk", back_populates="efficacy_records")
    user = relationship("User")
    knowledge_area = relationship("KnowledgeArea")
    
    # Check Constraints
    __table_args__ = (
        CheckConstraint("competency_before >= 0 AND competency_before <= 1", name='chk_comp_before_range'),
        CheckConstraint("competency_after IS NULL OR (competency_after >= 0 AND competency_after <= 1)", name='chk_comp_after_range'),
    )
    
    def __repr__(self):
        return f"<ContentEfficacy {self.efficacy_id} - {'Improved' if self.improved else 'Pending'}>"
```

---

## 3. PYDANTIC SCHEMAS ADDITIONS

```python
# app/schemas/content.py

class ContentFeedbackCreate(BaseModel):
    """Submit feedback on content."""
    was_helpful: bool
    feedback_text: Optional[str] = Field(None, max_length=500)

class ContentFeedbackResponse(BaseSchema, TimestampMixin):
    """Content feedback response."""
    feedback_id: UUID
    chunk_id: UUID
    user_id: UUID
    was_helpful: bool
    feedback_text: Optional[str]

class ContentMetricsResponse(BaseModel):
    """Admin view of content quality metrics."""
    chunk_id: UUID
    content_title: str
    
    # Usage stats
    total_reads: int
    total_feedback: int
    total_efficacy_records: int
    
    # Quality metrics
    helpfulness_score: Optional[float]  # 0-100
    efficacy_rate: Optional[float]  # 0-100
    avg_improvement: Optional[float]  # -1.0 to +1.0
    
    # Status
    review_status: str
    expert_reviewed: bool
    is_active: bool
    
    # Flags
    needs_review: bool  # True if helpfulness < 60% or efficacy < 40%

class ContentReviewUpdate(BaseModel):
    """Admin review decision."""
    review_status: str = Field(..., pattern="^(approved|flagged|rejected)$")
    expert_reviewed: bool = True
    review_notes: Optional[str] = None
```

---

## 4. API ENDPOINTS ADDITIONS

### 4.1 POST /v1/content/{chunk_id}/feedback

Submit feedback after reading content.

**Auth:** Required  
**Request:**
```json
{
  "was_helpful": true,
  "feedback_text": "Clear explanation of SWOT analysis"
}
```

**Response:** `201 Created`
```json
{
  "feedback_id": "uuid",
  "chunk_id": "uuid",
  "was_helpful": true,
  "created_at": "2025-10-24T10:30:00Z"
}
```

**Side Effects:**
- Creates content_feedback record
- If user has 10+ feedback entries and helpfulness < 60%, flag chunk for review
- Updates aggregate helpfulness score

---

### 4.2 GET /v1/admin/content/{chunk_id}/metrics

Get quality metrics for specific content.

**Auth:** Required (admin or super_admin)  
**Response:** `200 OK`
```json
{
  "chunk_id": "uuid",
  "content_title": "SWOT Analysis Techniques",
  "total_reads": 250,
  "total_feedback": 85,
  "total_efficacy_records": 180,
  "helpfulness_score": 87.5,
  "efficacy_rate": 72.3,
  "avg_improvement": 0.08,
  "review_status": "approved",
  "expert_reviewed": true,
  "is_active": true,
  "needs_review": false
}
```

---

### 4.3 GET /v1/admin/content/flagged

List content needing review.

**Auth:** Required (admin or super_admin)  
**Query Parameters:**
- `reason`: 'low_helpfulness' | 'low_efficacy' | 'pending_review'

**Response:** `200 OK`
```json
{
  "flagged_content": [
    {
      "chunk_id": "uuid",
      "content_title": "Porter's Five Forces",
      "flag_reason": "low_helpfulness",
      "helpfulness_score": 45.2,
      "total_feedback": 25,
      "review_status": "approved",
      "last_reviewed_at": "2025-09-15T10:00:00Z"
    }
  ],
  "total_flagged": 12
}
```

---

### 4.4 PATCH /v1/admin/content/{chunk_id}/review

Admin approves/rejects content after review.

**Auth:** Required (admin or super_admin)  
**Request:**
```json
{
  "review_status": "approved",
  "expert_reviewed": true,
  "review_notes": "Verified against BABOK v3 pp. 125-130. Accurate and clear."
}
```

**Response:** `200 OK`
```json
{
  "chunk_id": "uuid",
  "review_status": "approved",
  "is_active": true,
  "reviewed_at": "2025-10-24T10:30:00Z"
}
```

**Side Effects:**
- Updates chunk review_status and expert_reviewed
- If approved, sets is_active = true (visible to learners)
- If rejected, sets is_active = false (hidden)
- Creates security_log entry

---

## 5. ALGORITHM UPDATES

### 5.1 Updated Content Recommendation Algorithm

**File:** `app/services/content_recommendation.py`

```python
def calculate_content_score(
    chunk: ContentChunk,
    user_competencies: Dict[UUID, float],
    recent_reads: List[UUID]
) -> float:
    """
    Score content chunk with quality metrics.
    
    Updated weights (Decision #76):
    - 30% similarity (was 40%)
    - 25% knowledge gap (was 30%)
    - 15% difficulty match (was 20%)
    - 10% recency penalty (was 10%)
    - 10% helpfulness (NEW)
    - 10% efficacy (NEW)
    """
    
    # Only show approved, active content
    if not chunk.is_active or chunk.review_status != 'approved':
        return 0.0
    
    # Component 1: Vector similarity (0-1)
    similarity_score = chunk.similarity
    
    # Component 2: KA competency gap (inverse - recommend for weak areas)
    ka_competency = user_competencies[chunk.ka_id]
    gap_score = 1.0 - ka_competency
    
    # Component 3: Difficulty match
    difficulty_score = calculate_difficulty_match(chunk, ka_competency)
    
    # Component 4: Recency penalty (avoid recently read)
    if chunk.chunk_id in recent_reads:
        recency_penalty = 0.3
    else:
        recency_penalty = 1.0
    
    # Component 5: Helpfulness boost (NEW)
    helpfulness = chunk.helpfulness_score or 75.0  # Default 75% if no feedback yet
    helpfulness_boost = helpfulness / 100.0  # Normalize to 0-1
    
    # Component 6: Efficacy boost (NEW)
    efficacy = chunk.efficacy_rate or 70.0  # Default 70% if no data yet
    efficacy_boost = efficacy / 100.0  # Normalize to 0-1
    
    # Combine scores (updated weights)
    total_score = (
        similarity_score * 0.30 +
        gap_score * 0.25 +
        difficulty_score * 0.15 +
        recency_penalty * 0.10 +
        helpfulness_boost * 0.10 +
        efficacy_boost * 0.10
    )
    
    return total_score
```

### 5.2 Efficacy Measurement Job

**Background job to measure content efficacy:**

```python
# app/jobs/measure_content_efficacy.py

async def measure_content_efficacy():
    """
    Background job: Run every 6 hours
    Measures efficacy for content read 24+ hours ago
    """
    
    # Get efficacy records waiting for measurement (read >24hr ago, not measured)
    pending_records = db.query(ContentEfficacy).filter(
        ContentEfficacy.competency_after.is_(None),
        ContentEfficacy.read_at < datetime.now() - timedelta(hours=24)
    ).all()
    
    for record in pending_records:
        # Get user's current competency in that KA
        current_competency = get_user_competency(record.user_id, record.ka_id)
        
        # Update record
        record.competency_after = current_competency.competency_score
        record.measured_at = datetime.now()
        record.improved = current_competency.competency_score > record.competency_before
        record.improvement_amount = current_competency.competency_score - record.competency_before
        
        db.commit()
    
    # Flag chunks with low efficacy
    flag_low_efficacy_content(threshold=40.0)
```

---

## 6. ADMIN DASHBOARD VIEWS

### 6.1 Content Quality Dashboard

**Displays:**
- Overall content quality score (avg helpfulness)
- Flagged content count (needs review)
- Top performing content (>90% helpfulness)
- Bottom performing content (<60% helpfulness)
- Efficacy by KA (which KAs have best content)
- Pending reviews (status='pending')

**SQL Query:**
```sql
SELECT 
    c.chunk_id,
    c.content_title,
    c.ka_id,
    ka.ka_name,
    c.review_status,
    c.is_active,
    ch.total_feedback,
    ch.helpfulness_percentage,
    ce.total_reads,
    ce.efficacy_percentage,
    ce.avg_improvement,
    CASE 
        WHEN ch.helpfulness_percentage < 60 THEN 'low_helpfulness'
        WHEN ce.efficacy_percentage < 40 THEN 'low_efficacy'
        WHEN c.review_status = 'pending' THEN 'pending_review'
        ELSE 'healthy'
    END as flag_status
FROM content_chunks c
JOIN knowledge_areas ka ON c.ka_id = ka.ka_id
LEFT JOIN content_helpfulness ch ON c.chunk_id = ch.chunk_id
LEFT JOIN content_efficacy_stats ce ON c.chunk_id = ce.chunk_id
WHERE c.course_id = ?
ORDER BY flag_status DESC, ch.helpfulness_percentage ASC;
```

---

## 7. TESTING REQUIREMENTS

### 7.1 Unit Tests

```python
# tests/test_content_quality.py

def test_content_feedback_creation():
    """Test user can submit feedback."""
    feedback = create_feedback(
        chunk_id=chunk.chunk_id,
        user_id=user.user_id,
        was_helpful=True
    )
    assert feedback.was_helpful == True

def test_helpfulness_score_calculation():
    """Test helpfulness percentage calculation."""
    # Create 10 feedback entries: 8 helpful, 2 not helpful
    for i in range(8):
        create_feedback(chunk_id, user_id=f"user{i}", was_helpful=True)
    for i in range(2):
        create_feedback(chunk_id, user_id=f"user{i+8}", was_helpful=False)
    
    chunk = get_chunk(chunk_id)
    assert chunk.helpfulness_score == 80.0

def test_efficacy_measurement():
    """Test efficacy tracking after reading."""
    # User reads content
    efficacy = create_efficacy_record(
        chunk_id=chunk.chunk_id,
        user_id=user.user_id,
        competency_before=0.50
    )
    
    # 24 hours later, user practices and improves
    update_user_competency(user.user_id, ka_id, 0.60)
    
    # Background job measures efficacy
    measure_content_efficacy()
    
    # Verify
    efficacy = get_efficacy_record(efficacy.efficacy_id)
    assert efficacy.competency_after == 0.60
    assert efficacy.improved == True
    assert efficacy.improvement_amount == 0.10

def test_content_filtering_by_status():
    """Test only approved, active content is shown."""
    # Create chunks with different statuses
    pending = create_chunk(review_status='pending')
    approved = create_chunk(review_status='approved', is_active=True)
    rejected = create_chunk(review_status='rejected')
    
    # Get recommendations
    recommendations = get_content_recommendations(user_id)
    
    # Only approved, active chunks returned
    chunk_ids = [r.chunk_id for r in recommendations]
    assert approved.chunk_id in chunk_ids
    assert pending.chunk_id not in chunk_ids
    assert rejected.chunk_id not in chunk_ids

def test_flagging_low_quality_content():
    """Test automatic flagging of low-quality content."""
    # Create chunk with poor helpfulness
    for i in range(20):
        create_feedback(chunk_id, user_id=f"user{i}", was_helpful=(i < 8))  # 40% helpful
    
    # Should be flagged
    flagged = get_flagged_content(reason='low_helpfulness')
    assert chunk.chunk_id in [c.chunk_id for c in flagged]
```

### 7.2 Integration Tests

```python
def test_content_quality_flow():
    """Test complete content quality flow."""
    
    # 1. Admin uploads content (pending status)
    chunk = admin_create_content(
        content_text="...",
        source="BABOK v3 pp. 45",
        review_status='pending'
    )
    assert chunk.is_active == False  # Not visible yet
    
    # 2. Admin reviews and approves
    admin_approve_content(chunk.chunk_id)
    assert chunk.review_status == 'approved'
    assert chunk.is_active == True  # Now visible
    
    # 3. Learner reads content
    read_content(user_id, chunk.chunk_id)
    
    # 4. Learner submits feedback
    submit_feedback(chunk.chunk_id, was_helpful=True)
    
    # 5. Learner practices questions
    practice_session(user_id, ka_id)
    
    # 6. Background job measures efficacy
    measure_content_efficacy()
    
    # 7. Verify metrics updated
    metrics = get_content_metrics(chunk.chunk_id)
    assert metrics.helpfulness_score > 0
    assert metrics.efficacy_rate is not None
```

---

## 8. IMPLEMENTATION TIMELINE

**Days 12-14 (after core learning features):**

**Day 12: Database & Models**
- Add quality fields to content_chunks table
- Create content_feedback table
- Create content_efficacy table
- Update ContentChunk model
- Create ContentFeedback model
- Create ContentEfficacy model
- Write model tests

**Day 13: API Endpoints**
- POST /v1/content/{chunk_id}/feedback
- GET /v1/admin/content/{chunk_id}/metrics
- GET /v1/admin/content/flagged
- PATCH /v1/admin/content/{chunk_id}/review
- Write endpoint tests

**Day 14: Algorithm & Jobs**
- Update calculate_content_score() algorithm
- Create measure_content_efficacy() background job
- Create flag_low_quality_content() function
- Admin dashboard views
- Integration tests

---

## 9. SUCCESS METRICS

**Content Quality Goals:**
- ✅ 100% of active content has been expert reviewed
- ✅ 90%+ of active content has helpfulness >70%
- ✅ 80%+ of content shows competency improvement (efficacy)
- ✅ <5% of content flagged for quality issues
- ✅ All content has verified source references (BABOK page numbers)

**User Experience Goals:**
- ✅ Users report high satisfaction with recommendations
- ✅ Recommended content demonstrably improves test scores
- ✅ Low bounce rate on content (users finish reading)

---

## 10. ROLLOUT PLAN

**Phase 1: MVP (Days 12-14)**
- Pre-ingestion validation (expert review required)
- User feedback collection (thumbs up/down)
- Basic efficacy tracking
- Admin approval workflow
- Manual flagging of poor content

**Phase 2: Post-MVP (Month 2)**
- A/B testing framework
- Automated quality prediction
- Content improvement suggestions
- Collaborative filtering
- Machine learning quality model

**Phase 3: Scale (Month 3+)**
- Crowd-sourced content contributions
- Community voting system
- Content versioning
- Multi-language support

---

## CONCLUSION

This content quality evaluation system ensures that reading recommendations are:
1. **Accurate** (expert reviewed, source verified)
2. **Relevant** (vector similarity + knowledge gap matching)
3. **Effective** (proven to improve competency)
4. **High Quality** (user feedback >70% helpful)

**Status:** ✅ APPROVED - CRITICAL FOR MVP  
**Implementation:** Days 12-14 of sprint  
**Priority:** HIGH (user trust depends on content quality)

---

**Addendum Complete**

This system should be integrated into all TDD documents before transitioning to Claude Code implementation.