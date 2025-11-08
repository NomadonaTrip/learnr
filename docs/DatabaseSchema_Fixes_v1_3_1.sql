-- ============================================================================
-- Database Schema Fixes - Migration Script
-- Adaptive CBAP Learning Platform
-- ============================================================================
-- Version: 1.3.1 (Fixes for v1.3)
-- Date: October 24, 2025
-- Decision: #70 (Database Schema Review & Approval)
-- 
-- Purpose: Implements 4 required fixes identified in schema review
-- Estimated Time: 30 minutes
-- 
-- FIXES:
-- 1. [CRITICAL] Vector dimension correction (1536 â†’ 3072)
-- 2. Add validate_ka_weights() trigger function
-- 3. Add immutability trigger for security_logs
-- 4. Update password_hash comment (bcrypt â†’ Argon2id)
-- ============================================================================

-- Begin Transaction
BEGIN;

-- ============================================================================
-- FIX #1: CRITICAL - Correct Vector Dimension
-- ============================================================================
-- Issue: content_chunks.embedding uses VECTOR(1536) but text-embedding-3-large
--        actually produces 3072 dimensions
-- Impact: HIGH - Will cause runtime errors when inserting embeddings
-- Fix: Change VECTOR(1536) to VECTOR(3072)
-- ============================================================================

DO $$
BEGIN
    -- Check if pgvector extension exists
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE EXCEPTION 'pgvector extension not installed. Run: CREATE EXTENSION vector;';
    END IF;
END $$;

-- Drop existing index on embedding (will recreate after type change)
DROP INDEX IF EXISTS idx_chunks_embedding;

-- Change vector dimension from 1536 to 3072
ALTER TABLE content_chunks 
    ALTER COLUMN embedding TYPE VECTOR(3072);

-- Recreate index with correct dimension
CREATE INDEX idx_chunks_embedding 
    ON content_chunks 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);  -- Adjust lists based on dataset size

-- Update comment to reflect correct dimension
COMMENT ON COLUMN content_chunks.embedding IS 
    'OpenAI text-embedding-3-large (3072 dimensions) - used for semantic similarity search';

-- Verification query
DO $$
DECLARE
    v_dimension INTEGER;
BEGIN
    SELECT atttypmod INTO v_dimension
    FROM pg_attribute 
    WHERE attrelid = 'content_chunks'::regclass 
      AND attname = 'embedding';
    
    IF v_dimension = 3072 THEN
        RAISE NOTICE 'Fix #1 SUCCESS: Vector dimension is now 3072';
    ELSE
        RAISE EXCEPTION 'Fix #1 FAILED: Vector dimension is %, expected 3072', v_dimension;
    END IF;
END $$;

-- ============================================================================
-- FIX #2: Add validate_ka_weights() Trigger Function
-- ============================================================================
-- Issue: Trigger exists but function is not defined
-- Impact: MEDIUM - KA weight validation not enforced at database level
-- Fix: Create the trigger function
-- ============================================================================

CREATE OR REPLACE FUNCTION validate_ka_weights()
RETURNS TRIGGER AS $$
DECLARE
    total_weight DECIMAL(5,2);
    course_name_var VARCHAR(255);
BEGIN
    -- Calculate total weight for the course
    SELECT SUM(weight_percentage) 
    INTO total_weight
    FROM knowledge_areas
    WHERE course_id = NEW.course_id;
    
    -- Allow small floating-point imprecision (0.01%)
    IF ABS(total_weight - 100.00) > 0.01 THEN
        -- Get course name for better error message
        SELECT c.course_name INTO course_name_var
        FROM courses c
        WHERE c.course_id = NEW.course_id;
        
        RAISE EXCEPTION 
            'Knowledge area weights must sum to exactly 100%% for course "%" (course_id: %). Current sum: %%',
            course_name_var, NEW.course_id, total_weight;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Ensure trigger exists (recreate if needed)
DROP TRIGGER IF EXISTS trg_validate_ka_weights ON knowledge_areas;

CREATE TRIGGER trg_validate_ka_weights
    AFTER INSERT OR UPDATE ON knowledge_areas
    FOR EACH ROW 
    EXECUTE FUNCTION validate_ka_weights();

-- Verification query
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'validate_ka_weights'
    ) THEN
        RAISE NOTICE 'Fix #2 SUCCESS: validate_ka_weights() function created';
    ELSE
        RAISE EXCEPTION 'Fix #2 FAILED: Function not found';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trg_validate_ka_weights'
    ) THEN
        RAISE NOTICE 'Fix #2 SUCCESS: Trigger trg_validate_ka_weights attached';
    ELSE
        RAISE EXCEPTION 'Fix #2 FAILED: Trigger not found';
    END IF;
END $$;

-- ============================================================================
-- FIX #3: Add Immutability Trigger for security_logs
-- ============================================================================
-- Issue: security_logs documented as immutable but no trigger enforces it
-- Impact: MEDIUM - Security audit trail could be modified/deleted
-- Fix: Create trigger to prevent UPDATE/DELETE operations
-- ============================================================================

CREATE OR REPLACE FUNCTION prevent_security_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 
        'Security logs are immutable and cannot be modified or deleted. '
        'This is a compliance requirement (GDPR Article 33, SOC 2). '
        'Attempted operation: % on log_id: %', 
        TG_OP, OLD.log_id;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for UPDATE operations
DROP TRIGGER IF EXISTS trg_prevent_security_log_update ON security_logs;

CREATE TRIGGER trg_prevent_security_log_update
    BEFORE UPDATE ON security_logs
    FOR EACH ROW 
    EXECUTE FUNCTION prevent_security_log_modification();

-- Create trigger for DELETE operations
DROP TRIGGER IF EXISTS trg_prevent_security_log_delete ON security_logs;

CREATE TRIGGER trg_prevent_security_log_delete
    BEFORE DELETE ON security_logs
    FOR EACH ROW 
    EXECUTE FUNCTION prevent_security_log_modification();

-- Add comment to table explaining immutability
COMMENT ON TABLE security_logs IS 
    'Immutable audit trail for security events. '
    'Records cannot be modified or deleted (enforced by triggers). '
    'Compliance: GDPR Article 33, SOC 2 Security Principle. '
    'Decision #51, #70.';

-- Verification query
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'prevent_security_log_modification'
    ) THEN
        RAISE NOTICE 'Fix #3 SUCCESS: prevent_security_log_modification() function created';
    ELSE
        RAISE EXCEPTION 'Fix #3 FAILED: Function not found';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trg_prevent_security_log_update'
    ) THEN
        RAISE NOTICE 'Fix #3 SUCCESS: UPDATE trigger attached';
    ELSE
        RAISE EXCEPTION 'Fix #3 FAILED: UPDATE trigger not found';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trg_prevent_security_log_delete'
    ) THEN
        RAISE NOTICE 'Fix #3 SUCCESS: DELETE trigger attached';
    ELSE
        RAISE EXCEPTION 'Fix #3 FAILED: DELETE trigger not found';
    END IF;
END $$;

-- ============================================================================
-- FIX #4: Update password_hash Comment
-- ============================================================================
-- Issue: Comment says "bcrypt" but Decision #53 specifies Argon2id
-- Impact: LOW - Documentation only, but creates confusion
-- Fix: Update comment to reflect correct algorithm
-- ============================================================================

COMMENT ON COLUMN users.password_hash IS 
    'Password hash using Argon2id algorithm (Decision #53). '
    'Argon2id provides memory-hard protection against GPU-based attacks. '
    'Cost parameters: memory=65536, iterations=3, parallelism=4';

-- Verification query
DO $$
DECLARE
    v_comment TEXT;
BEGIN
    SELECT col_description('users'::regclass, 2) INTO v_comment;
    
    IF v_comment LIKE '%Argon2id%' THEN
        RAISE NOTICE 'Fix #4 SUCCESS: Comment updated to reference Argon2id';
    ELSE
        RAISE EXCEPTION 'Fix #4 FAILED: Comment not updated correctly';
    END IF;
END $$;

-- ============================================================================
-- FINAL VERIFICATION
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Database Schema Fixes - Migration Complete';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Version: 1.3.1';
    RAISE NOTICE 'Date: October 24, 2025';
    RAISE NOTICE '';
    RAISE NOTICE 'All 4 fixes have been successfully applied:';
    RAISE NOTICE '  âœ“ Fix #1: Vector dimension corrected (1536 â†’ 3072)';
    RAISE NOTICE '  âœ“ Fix #2: validate_ka_weights() function added';
    RAISE NOTICE '  âœ“ Fix #3: security_logs immutability enforced';
    RAISE NOTICE '  âœ“ Fix #4: password_hash comment updated';
    RAISE NOTICE '';
    RAISE NOTICE 'Schema is now PRODUCTION READY.';
    RAISE NOTICE '============================================================';
END $$;

-- Commit Transaction
COMMIT;

-- ============================================================================
-- POST-MIGRATION TESTING
-- ============================================================================

-- Test #1: Verify vector dimension
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    numeric_precision
FROM information_schema.columns
WHERE table_name = 'content_chunks' 
  AND column_name = 'embedding';

-- Test #2: Try to insert KA with invalid weights (should fail)
-- Uncomment to test:
-- INSERT INTO knowledge_areas (course_id, ka_code, ka_name, ka_number, weight_percentage)
-- SELECT course_id, 'TEST', 'Test KA', 99, 50.00
-- FROM courses WHERE course_code = 'CBAP';
-- Expected: ERROR - weights don't sum to 100%

-- Test #3: Try to modify security log (should fail)
-- Uncomment to test:
-- UPDATE security_logs SET severity = 'CRITICAL' WHERE severity = 'INFO' LIMIT 1;
-- Expected: ERROR - security logs are immutable

-- Test #4: Verify password_hash comment
SELECT 
    col_description('users'::regclass, 
        (SELECT ordinal_position FROM information_schema.columns 
         WHERE table_name = 'users' AND column_name = 'password_hash')
    ) AS password_hash_comment;

-- ============================================================================
-- ROLLBACK SCRIPT (Emergency Use Only)
-- ============================================================================
-- Uncomment and run if you need to rollback these changes
-- WARNING: Only use if absolutely necessary!

/*
BEGIN;

-- Rollback Fix #1: Revert to VECTOR(1536) - NOT RECOMMENDED
-- ALTER TABLE content_chunks ALTER COLUMN embedding TYPE VECTOR(1536);
-- DROP INDEX IF EXISTS idx_chunks_embedding;
-- CREATE INDEX idx_chunks_embedding ON content_chunks USING ivfflat (embedding vector_cosine_ops);

-- Rollback Fix #2: Drop function and trigger
DROP TRIGGER IF EXISTS trg_validate_ka_weights ON knowledge_areas;
DROP FUNCTION IF EXISTS validate_ka_weights();

-- Rollback Fix #3: Drop immutability triggers
DROP TRIGGER IF EXISTS trg_prevent_security_log_update ON security_logs;
DROP TRIGGER IF EXISTS trg_prevent_security_log_delete ON security_logs;
DROP FUNCTION IF EXISTS prevent_security_log_modification();

-- Rollback Fix #4: Revert comment
COMMENT ON COLUMN users.password_hash IS 'bcrypt';

COMMIT;
*/

-- ============================================================================
-- NOTES
-- ============================================================================
-- 
-- Migration Success Criteria:
-- âœ“ All 4 fixes applied without errors
-- âœ“ All verification queries pass
-- âœ“ No data loss
-- âœ“ All existing data compatible with changes
-- 
-- Post-Migration Checklist:
-- â–¡ Run post-migration tests (above)
-- â–¡ Update schema documentation (TDDoc_DatabaseSchema.md) to v1.3.1
-- â–¡ Update Data Models (TDDoc_DataModels.md) to reference correct vector dimension
-- â–¡ Notify team that schema is production-ready
-- â–¡ Proceed to API Endpoints (TDDoc_API_Endpoints.md)
-- 
-- Performance Impact:
-- - Fix #1: Minimal (index rebuild ~1-2 seconds for empty table)
-- - Fix #2: None (trigger only fires on KA changes)
-- - Fix #3: Minimal (trigger overhead ~0.1ms per security log write)
-- - Fix #4: None (comment only)
-- 
-- Estimated Total Migration Time: 2-5 seconds (for empty database)
-- 
-- ============================================================================
