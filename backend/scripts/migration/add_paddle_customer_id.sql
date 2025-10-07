-- Add paddle_customer_id column to subscriptions table
-- This is needed for webhook lookups when custom_data is null

-- Add the column if it doesn't exist
ALTER TABLE public.subscriptions 
ADD COLUMN IF NOT EXISTS paddle_customer_id TEXT;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_subscriptions_paddle_customer_id 
ON public.subscriptions(paddle_customer_id);

-- Add comment
COMMENT ON COLUMN public.subscriptions.paddle_customer_id IS 'Paddle customer ID for webhook lookups';

-- Update existing subscriptions to populate paddle_customer_id if possible
-- This would need to be done via the application or manually based on your data
