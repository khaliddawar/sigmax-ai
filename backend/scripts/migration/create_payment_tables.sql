-- Create payment and subscription tables for Simply app
-- Run this after authentication tables are set up

-- =====================================================
-- SUBSCRIPTIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    paddle_subscription_id TEXT UNIQUE,
    plan TEXT NOT NULL CHECK (plan IN ('free', 'premium', 'enterprise')),
    status TEXT NOT NULL CHECK (status IN ('active', 'cancelled', 'expired', 'past_due', 'trialing', 'paused')),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    -- Foreign key to user_profiles table
    CONSTRAINT fk_subscriptions_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES auth.users(id) 
        ON DELETE CASCADE
);

-- =====================================================
-- PAYMENTS TABLE 
-- =====================================================
CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    subscription_id UUID,
    paddle_transaction_id TEXT UNIQUE,
    amount DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'failed', 'refunded', 'cancelled')),
    payment_method TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    
    -- Foreign keys
    CONSTRAINT fk_payments_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES auth.users(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_payments_subscription_id 
        FOREIGN KEY (subscription_id) 
        REFERENCES public.subscriptions(id) 
        ON DELETE SET NULL
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON public.subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_paddle_id ON public.subscriptions(paddle_subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON public.subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON public.payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_subscription_id ON public.payments(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payments_paddle_id ON public.payments(paddle_transaction_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON public.payments(status);

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

-- Users can only see their own subscriptions
CREATE POLICY "Users can view own subscriptions" ON public.subscriptions
    FOR SELECT 
    TO authenticated
    USING (auth.uid() = user_id);

-- Users can only see their own payments  
CREATE POLICY "Users can view own payments" ON public.payments
    FOR SELECT 
    TO authenticated  
    USING (auth.uid() = user_id);

-- Service role can do everything (for webhooks and admin operations)
CREATE POLICY "Service role can manage subscriptions" ON public.subscriptions
    FOR ALL 
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role can manage payments" ON public.payments
    FOR ALL 
    TO service_role  
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- UPDATE TRIGGERS 
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_subscriptions_updated_at 
    BEFORE UPDATE ON public.subscriptions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function to get user's current subscription
CREATE OR REPLACE FUNCTION public.get_user_subscription(user_uuid UUID)
RETURNS TABLE(
    subscription_id UUID,
    plan TEXT,
    status TEXT,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN,
    cancelled_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.plan,
        s.status,
        s.current_period_start,
        s.current_period_end,
        s.cancel_at_period_end,
        s.cancelled_at
    FROM public.subscriptions s
    WHERE s.user_id = user_uuid
    AND s.status IN ('active', 'trialing', 'past_due')
    ORDER BY s.created_at DESC
    LIMIT 1;
END;
$$;

-- Function to check if user has active subscription
CREATE OR REPLACE FUNCTION public.has_active_subscription(user_uuid UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    subscription_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO subscription_count
    FROM public.subscriptions
    WHERE user_id = user_uuid
    AND status IN ('active', 'trialing')
    AND (current_period_end IS NULL OR current_period_end > NOW());
    
    RETURN subscription_count > 0;
END;
$$;

-- Grant permissions to functions
GRANT EXECUTE ON FUNCTION public.get_user_subscription(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.has_active_subscription(UUID) TO authenticated;

-- =====================================================
-- INITIAL DATA SETUP
-- =====================================================

-- Update existing user_profiles to include subscription info
-- This will link existing users to their subscription data
UPDATE public.user_profiles 
SET plan_limits = COALESCE(plan_limits, '{}'::jsonb) || '{"subscription_managed": true}'::jsonb
WHERE plan_type IN ('premium', 'enterprise');

COMMENT ON TABLE public.subscriptions IS 'Stores user subscription data from Paddle';
COMMENT ON TABLE public.payments IS 'Stores payment transaction data from Paddle';
COMMENT ON FUNCTION public.get_user_subscription(UUID) IS 'Returns current active subscription for a user';
COMMENT ON FUNCTION public.has_active_subscription(UUID) IS 'Checks if user has an active subscription';