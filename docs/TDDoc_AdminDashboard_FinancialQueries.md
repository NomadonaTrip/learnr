# Admin Dashboard - Financial Metrics Queries
# Adaptive CBAP Learning Platform

**Version:** 1.0  
**Date:** October 24, 2025  
**Related:** TDDoc_DatabaseSchema.md v1.3 (Decision #66)

---

## Overview

This document provides SQL queries for all financial metrics displayed in the admin dashboard. These queries are optimized for performance and use the financial infrastructure tables defined in Decision #66.

---

## 1. Core Financial Health Indicators

### Total Revenue (Gross Sales)

```sql
-- Daily revenue
SELECT 
    DATE(occurred_at) as date,
    SUM(amount) as gross_revenue
FROM revenue_events
WHERE event_type = 'payment_succeeded'
  AND occurred_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(occurred_at)
ORDER BY date DESC;

-- Monthly revenue
SELECT 
    DATE_TRUNC('month', occurred_at) as month,
    SUM(amount) as gross_revenue
FROM revenue_events
WHERE event_type = 'payment_succeeded'
GROUP BY month
ORDER BY month DESC
LIMIT 12;

-- YTD revenue
SELECT 
    SUM(amount) as ytd_revenue
FROM revenue_events
WHERE event_type = 'payment_succeeded'
  AND EXTRACT(YEAR FROM occurred_at) = EXTRACT(YEAR FROM CURRENT_DATE);
```

---

### Net Revenue

```sql
-- Net revenue (after fees and refunds)
SELECT 
    DATE_TRUNC('month', occurred_at) as month,
    SUM(net_amount) as net_revenue
FROM revenue_events
GROUP BY month
ORDER BY month DESC
LIMIT 12;

-- Current month net revenue
SELECT 
    SUM(net_amount) as current_month_net_revenue
FROM revenue_events
WHERE DATE_TRUNC('month', occurred_at) = DATE_TRUNC('month', CURRENT_DATE);
```

---

### Monthly Recurring Revenue (MRR)

```sql
-- Current MRR
SELECT 
    SUM(CASE 
        WHEN sp.billing_interval = 'monthly' THEN sp.price_amount
        WHEN sp.billing_interval = 'annual' THEN sp.price_amount / 12
        ELSE 0
    END) as mrr
FROM subscriptions s
JOIN subscription_plans sp ON s.plan_id = sp.plan_id
WHERE s.status = 'active';

-- MRR trend over time
SELECT 
    DATE_TRUNC('month', s.created_at) as month,
    SUM(CASE 
        WHEN sp.billing_interval = 'monthly' THEN sp.price_amount
        WHEN sp.billing_interval = 'annual' THEN sp.price_amount / 12
        ELSE 0
    END) as mrr
FROM subscriptions s
JOIN subscription_plans sp ON s.plan_id = sp.plan_id
WHERE s.status = 'active'
GROUP BY month
ORDER BY month DESC;
```

---

### Annual Recurring Revenue (ARR)

```sql
-- Current ARR
SELECT 
    SUM(CASE 
        WHEN sp.billing_interval = 'monthly' THEN sp.price_amount * 12
        WHEN sp.billing_interval = 'annual' THEN sp.price_amount
        ELSE 0
    END) as arr
FROM subscriptions s
JOIN subscription_plans sp ON s.plan_id = sp.plan_id
WHERE s.status = 'active';
```

---

### Cash Flow (Inflow vs Outflow)

```sql
-- Monthly cash flow
SELECT 
    DATE_TRUNC('month', occurred_at) as month,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as inflow,
    ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)) as outflow,
    SUM(amount) as net_cash_flow
FROM revenue_events
GROUP BY month
ORDER BY month DESC;
```

---

### Gross Margin

```sql
-- Gross Margin = (Net Revenue - COGS) / Net Revenue
-- For SaaS: COGS ≈ Stripe fees
SELECT 
    (SUM(net_amount) / NULLIF(SUM(amount), 0)) * 100 as gross_margin_percentage
FROM revenue_events
WHERE event_type = 'payment_succeeded'
  AND occurred_at >= NOW() - INTERVAL '30 days';
```

---

## 2. Transaction & Payment Details

### Number of Transactions

```sql
-- Total successful transactions
SELECT COUNT(*) as total_transactions
FROM payments
WHERE status = 'succeeded';

-- Transactions by time period
SELECT 
    DATE_TRUNC('day', paid_at) as date,
    COUNT(*) as transaction_count
FROM payments
WHERE status = 'succeeded'
  AND paid_at >= NOW() - INTERVAL '30 days'
GROUP BY date
ORDER BY date DESC;
```

---

### Average Transaction Value (ATV)

```sql
-- Overall ATV
SELECT 
    AVG(amount) as average_transaction_value
FROM payments
WHERE status = 'succeeded';

-- ATV by month
SELECT 
    DATE_TRUNC('month', paid_at) as month,
    AVG(amount) as atv
FROM payments
WHERE status = 'succeeded'
GROUP BY month
ORDER BY month DESC;
```

---

### Payment Methods Breakdown

```sql
-- Revenue by payment method
SELECT 
    payment_method_type,
    payment_method_brand,
    COUNT(*) as transaction_count,
    SUM(amount) as total_revenue,
    ROUND((SUM(amount) / (SELECT SUM(amount) FROM payments WHERE status = 'succeeded')) * 100, 2) as revenue_percentage
FROM payments
WHERE status = 'succeeded'
GROUP BY payment_method_type, payment_method_brand
ORDER BY total_revenue DESC;

-- Payment method trend over time
SELECT 
    DATE_TRUNC('month', paid_at) as month,
    payment_method_brand,
    COUNT(*) as transaction_count,
    SUM(amount) as revenue
FROM payments
WHERE status = 'succeeded'
GROUP BY month, payment_method_brand
ORDER BY month DESC, revenue DESC;
```

---

### Payment Success Rate

```sql
-- Overall success rate
SELECT 
    COUNT(*) FILTER (WHERE status = 'succeeded') as successful_payments,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_payments,
    (COUNT(*) FILTER (WHERE status = 'succeeded')::FLOAT / NULLIF(COUNT(*), 0)) * 100 as success_rate_percentage
FROM payments;

-- Success rate by payment method
SELECT 
    payment_method_brand,
    COUNT(*) FILTER (WHERE status = 'succeeded') as successful,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    (COUNT(*) FILTER (WHERE status = 'succeeded')::FLOAT / NULLIF(COUNT(*), 0)) * 100 as success_rate
FROM payments
GROUP BY payment_method_brand
ORDER BY success_rate DESC;
```

---

### Refund Rate

```sql
-- Overall refund rate
SELECT 
    (COUNT(DISTINCT r.payment_id)::FLOAT / NULLIF(COUNT(DISTINCT p.payment_id), 0)) * 100 as refund_rate_percentage
FROM payments p
LEFT JOIN refunds r ON p.payment_id = r.payment_id AND r.status = 'succeeded'
WHERE p.status IN ('succeeded', 'refunded');

-- Refund rate by month
SELECT 
    DATE_TRUNC('month', p.paid_at) as month,
    COUNT(DISTINCT p.payment_id) as total_payments,
    COUNT(DISTINCT r.payment_id) as refunded_payments,
    (COUNT(DISTINCT r.payment_id)::FLOAT / NULLIF(COUNT(DISTINCT p.payment_id), 0)) * 100 as refund_rate
FROM payments p
LEFT JOIN refunds r ON p.payment_id = r.payment_id AND r.status = 'succeeded'
WHERE p.status IN ('succeeded', 'refunded')
GROUP BY month
ORDER BY month DESC;
```

---

### Chargeback Rate

```sql
-- Overall chargeback rate
SELECT 
    (COUNT(DISTINCT c.payment_id)::FLOAT / NULLIF(COUNT(DISTINCT p.payment_id), 0)) * 100 as chargeback_rate_percentage
FROM payments p
LEFT JOIN chargebacks c ON p.payment_id = c.payment_id
WHERE p.status IN ('succeeded', 'disputed');

-- Chargeback rate by month
SELECT 
    DATE_TRUNC('month', p.paid_at) as month,
    COUNT(DISTINCT p.payment_id) as total_payments,
    COUNT(DISTINCT c.payment_id) as chargebacks,
    (COUNT(DISTINCT c.payment_id)::FLOAT / NULLIF(COUNT(DISTINCT p.payment_id), 0)) * 100 as chargeback_rate
FROM payments p
LEFT JOIN chargebacks c ON p.payment_id = c.payment_id
WHERE p.status IN ('succeeded', 'disputed')
GROUP BY month
ORDER BY month DESC;
```

---

## 3. Customer-Level Financial Insights

### Customer Lifetime Value (CLV)

```sql
-- CLV per user
SELECT 
    user_id,
    SUM(amount) as lifetime_value
FROM payments
WHERE status IN ('succeeded', 'refunded')
GROUP BY user_id
ORDER BY lifetime_value DESC;

-- Average CLV
SELECT 
    AVG(total_spent) as average_clv
FROM (
    SELECT 
        user_id,
        SUM(amount) as total_spent
    FROM payments
    WHERE status IN ('succeeded', 'refunded')
    GROUP BY user_id
) as user_totals;

-- CLV by cohort (sign-up month)
SELECT 
    DATE_TRUNC('month', u.created_at) as cohort_month,
    COUNT(DISTINCT u.user_id) as users_in_cohort,
    AVG(p.total_spent) as avg_clv
FROM users u
LEFT JOIN (
    SELECT 
        user_id,
        SUM(amount) as total_spent
    FROM payments
    WHERE status IN ('succeeded', 'refunded')
    GROUP BY user_id
) p ON u.user_id = p.user_id
GROUP BY cohort_month
ORDER BY cohort_month DESC;
```

---

### Customer Acquisition Cost (CAC)

```sql
-- Average CAC (requires acquisition_cost field)
SELECT 
    AVG(acquisition_cost) as average_cac
FROM user_profiles
WHERE acquisition_cost IS NOT NULL;

-- CAC by channel
SELECT 
    acquisition_channel,
    COUNT(*) as users_acquired,
    AVG(acquisition_cost) as avg_cac,
    SUM(acquisition_cost) as total_acquisition_cost
FROM user_profiles
WHERE acquisition_cost IS NOT NULL
GROUP BY acquisition_channel
ORDER BY total_acquisition_cost DESC;
```

---

### Revenue per Active User (RPAU)

```sql
-- Monthly RPAU
SELECT 
    (SELECT SUM(amount) 
     FROM payments 
     WHERE status = 'succeeded' 
       AND paid_at >= NOW() - INTERVAL '30 days')
    /
    NULLIF((SELECT COUNT(DISTINCT user_id) 
            FROM sessions 
            WHERE started_at >= NOW() - INTERVAL '30 days'), 0)
    as rpau;
```

---

### Churn Rate

```sql
-- Monthly churn rate
SELECT 
    DATE_TRUNC('month', canceled_at) as month,
    COUNT(*) as churned_subscriptions,
    (SELECT COUNT(*) 
     FROM subscriptions 
     WHERE status = 'active' 
       AND created_at <= DATE_TRUNC('month', canceled_at)) as active_at_month_start,
    (COUNT(*)::FLOAT / NULLIF((SELECT COUNT(*) 
                                FROM subscriptions 
                                WHERE status = 'active' 
                                  AND created_at <= DATE_TRUNC('month', canceled_at)), 0)) * 100 as churn_rate_percentage
FROM subscriptions
WHERE status = 'canceled'
  AND canceled_at IS NOT NULL
GROUP BY month
ORDER BY month DESC;
```

---

## 4. Developer-Focused / Infrastructure-Aware Metrics

### API Call Volume vs Revenue

```sql
-- This requires application-level tracking
-- Conceptual query - actual implementation depends on API logging
SELECT 
    DATE_TRUNC('day', api_called_at) as date,
    COUNT(*) as api_calls,
    SUM(revenue_generated) as revenue
FROM api_call_logs
GROUP BY date
ORDER BY date DESC;
```

---

### Compute Cost per Transaction

```sql
-- Requires cost tracking per transaction
-- Conceptual query
SELECT 
    AVG(compute_cost) as avg_compute_cost_per_transaction
FROM payments
WHERE compute_cost IS NOT NULL;
```

---

### Payment Gateway Fees

```sql
-- Total Stripe fees
SELECT 
    DATE_TRUNC('month', paid_at) as month,
    SUM(stripe_fee) as total_stripe_fees,
    SUM(amount) as total_revenue,
    (SUM(stripe_fee) / NULLIF(SUM(amount), 0)) * 100 as fee_percentage
FROM payments
WHERE status = 'succeeded'
GROUP BY month
ORDER BY month DESC;

-- Fees by payment method
SELECT 
    payment_method_brand,
    SUM(stripe_fee) as total_fees,
    COUNT(*) as transaction_count,
    AVG(stripe_fee) as avg_fee_per_transaction
FROM payments
WHERE status = 'succeeded'
GROUP BY payment_method_brand
ORDER BY total_fees DESC;
```

---

### Failed Transaction Logs

```sql
-- Failed transactions by reason
SELECT 
    failure_code,
    COUNT(*) as failure_count,
    failure_message
FROM payments
WHERE status = 'failed'
GROUP BY failure_code, failure_message
ORDER BY failure_count DESC;

-- Failed transactions trend
SELECT 
    DATE_TRUNC('day', created_at) as date,
    failure_code,
    COUNT(*) as failures
FROM payments
WHERE status = 'failed'
GROUP BY date, failure_code
ORDER BY date DESC, failures DESC;
```

---

## 5. Forecasting & Trend Analytics

### Revenue Growth Rate (MoM/YoY)

```sql
-- Month-over-Month growth
WITH monthly_revenue AS (
    SELECT 
        DATE_TRUNC('month', occurred_at) as month,
        SUM(net_amount) as revenue
    FROM revenue_events
    WHERE event_type = 'payment_succeeded'
    GROUP BY month
)
SELECT 
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY month) as previous_month_revenue,
    ((revenue - LAG(revenue) OVER (ORDER BY month)) / NULLIF(LAG(revenue) OVER (ORDER BY month), 0)) * 100 as mom_growth_rate
FROM monthly_revenue
ORDER BY month DESC;

-- Year-over-Year growth
WITH yearly_revenue AS (
    SELECT 
        EXTRACT(YEAR FROM occurred_at) as year,
        SUM(net_amount) as revenue
    FROM revenue_events
    WHERE event_type = 'payment_succeeded'
    GROUP BY year
)
SELECT 
    year,
    revenue,
    LAG(revenue) OVER (ORDER BY year) as previous_year_revenue,
    ((revenue - LAG(revenue) OVER (ORDER BY year)) / NULLIF(LAG(revenue) OVER (ORDER BY year), 0)) * 100 as yoy_growth_rate
FROM yearly_revenue
ORDER BY year DESC;
```

---

### Projected Runway

```sql
-- Requires burn rate data
-- Conceptual query
WITH monthly_metrics AS (
    SELECT 
        DATE_TRUNC('month', occurred_at) as month,
        SUM(net_amount) as net_revenue
    FROM revenue_events
    GROUP BY month
    ORDER BY month DESC
    LIMIT 3
),
avg_burn AS (
    SELECT AVG(net_revenue) as avg_monthly_burn
    FROM monthly_metrics
),
current_cash AS (
    -- Requires cash balance tracking
    SELECT cash_balance FROM company_financials ORDER BY recorded_at DESC LIMIT 1
)
SELECT 
    (SELECT cash_balance FROM current_cash) / NULLIF((SELECT avg_monthly_burn FROM avg_burn), 0) as runway_months;
```

---

### Revenue Forecast

```sql
-- Simple linear forecast based on last 6 months
WITH monthly_revenue AS (
    SELECT 
        DATE_TRUNC('month', occurred_at) as month,
        SUM(net_amount) as revenue,
        ROW_NUMBER() OVER (ORDER BY DATE_TRUNC('month', occurred_at)) as month_number
    FROM revenue_events
    WHERE event_type = 'payment_succeeded'
      AND occurred_at >= NOW() - INTERVAL '6 months'
    GROUP BY month
)
SELECT 
    month,
    revenue as actual_revenue,
    -- Simple trend projection
    AVG(revenue) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as moving_avg,
    FIRST_VALUE(revenue) OVER (ORDER BY month) + 
        (month_number - 1) * (LAST_VALUE(revenue) OVER (ORDER BY month ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) - 
                               FIRST_VALUE(revenue) OVER (ORDER BY month)) / 5.0 as linear_forecast
FROM monthly_revenue
ORDER BY month DESC;
```

---

### Cohort Revenue Retention

```sql
-- Revenue retention by signup cohort
WITH user_cohorts AS (
    SELECT 
        user_id,
        DATE_TRUNC('month', created_at) as cohort_month
    FROM users
),
cohort_revenue AS (
    SELECT 
        uc.cohort_month,
        DATE_TRUNC('month', p.paid_at) as revenue_month,
        SUM(p.amount) as revenue,
        COUNT(DISTINCT p.user_id) as paying_users
    FROM user_cohorts uc
    JOIN payments p ON uc.user_id = p.user_id
    WHERE p.status = 'succeeded'
    GROUP BY uc.cohort_month, revenue_month
)
SELECT 
    cohort_month,
    revenue_month,
    revenue,
    paying_users,
    revenue / FIRST_VALUE(revenue) OVER (PARTITION BY cohort_month ORDER BY revenue_month) * 100 as revenue_retention_percentage
FROM cohort_revenue
ORDER BY cohort_month DESC, revenue_month;
```

---

## 6. Alert & Monitoring Queries

### Chargebacks Needing Attention

```sql
-- Urgent: Evidence due soon
SELECT 
    c.chargeback_id,
    c.disputed_at,
    c.evidence_due_by,
    c.amount,
    u.email as user_email,
    p.payment_id,
    EXTRACT(DAY FROM (c.evidence_due_by - NOW())) as days_until_due
FROM chargebacks c
JOIN payments p ON c.payment_id = p.payment_id
JOIN users u ON c.user_id = u.user_id
WHERE c.status = 'warning_needs_response'
  AND c.evidence_due_by IS NOT NULL
  AND c.evidence_due_by <= NOW() + INTERVAL '7 days'
ORDER BY c.evidence_due_by ASC;
```

---

### Failed Payments (Last 24 Hours)

```sql
SELECT 
    p.payment_id,
    p.created_at,
    p.amount,
    p.failure_code,
    p.failure_message,
    u.email as user_email,
    s.subscription_id
FROM payments p
JOIN users u ON p.user_id = u.user_id
LEFT JOIN subscriptions s ON p.subscription_id = s.subscription_id
WHERE p.status = 'failed'
  AND p.created_at >= NOW() - INTERVAL '24 hours'
ORDER BY p.created_at DESC;
```

---

### High Refund Activity Alert

```sql
-- Alert if refund rate > 5% in last 7 days
WITH refund_metrics AS (
    SELECT 
        COUNT(DISTINCT p.payment_id) as total_payments,
        COUNT(DISTINCT r.payment_id) as refunded_payments,
        (COUNT(DISTINCT r.payment_id)::FLOAT / NULLIF(COUNT(DISTINCT p.payment_id), 0)) * 100 as refund_rate
    FROM payments p
    LEFT JOIN refunds r ON p.payment_id = r.payment_id AND r.status = 'succeeded'
    WHERE p.paid_at >= NOW() - INTERVAL '7 days'
      AND p.status IN ('succeeded', 'refunded')
)
SELECT 
    *,
    CASE 
        WHEN refund_rate > 5 THEN 'ALERT: High refund rate'
        ELSE 'Normal'
    END as alert_status
FROM refund_metrics;
```

---

## Performance Optimization Notes

1. **Indexes Required:**
   - All datetime columns should have indexes for time-range queries
   - Foreign keys should have indexes (already included in schema)
   - Composite indexes on (occurred_at, event_type) for revenue_events

2. **Materialized Views:**
   - Consider materialized views for complex aggregations (MRR, ARR)
   - Refresh hourly or daily depending on needs

3. **Query Optimization:**
   - Use DATE_TRUNC consistently for time-based grouping
   - Limit result sets for dashboard widgets (LIMIT 100)
   - Use EXPLAIN ANALYZE to identify slow queries

---

## API Endpoint Mapping

These queries should be exposed via REST API endpoints:

- `GET /api/admin/metrics/revenue/total` → Total Revenue query
- `GET /api/admin/metrics/revenue/net` → Net Revenue query
- `GET /api/admin/metrics/mrr` → MRR query
- `GET /api/admin/metrics/arr` → ARR query
- `GET /api/admin/metrics/transactions/count` → Transaction count
- `GET /api/admin/metrics/transactions/atv` → ATV query
- `GET /api/admin/metrics/payments/methods` → Payment methods breakdown
- `GET /api/admin/metrics/refunds/rate` → Refund rate
- `GET /api/admin/metrics/chargebacks/rate` → Chargeback rate
- `GET /api/admin/metrics/customers/clv` → CLV query
- `GET /api/admin/metrics/customers/cac` → CAC query
- `GET /api/admin/metrics/churn` → Churn rate
- `GET /api/admin/alerts/chargebacks` → Urgent chargebacks
- `GET /api/admin/alerts/failed-payments` → Recent failures

---

**Document Status:** READY FOR IMPLEMENTATION  
**Next Step:** Create API endpoints using these queries
