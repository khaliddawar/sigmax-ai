-- =====================================================
-- SignalScope Database Schema for Supabase
-- =====================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------
-- Messages Table (Raw captured data)
-- -----------------------------------------------------
DROP TABLE IF EXISTS messages CASCADE;
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id TEXT UNIQUE NOT NULL,
    platform TEXT NOT NULL,
    author TEXT,
    content TEXT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL,
    importance_score INTEGER CHECK (importance_score >= 0 AND importance_score <= 10),
    tickers TEXT[],
    sentiment TEXT CHECK (sentiment IN ('bullish', 'bearish', 'neutral')),
    trading_signal JSONB,
    batch_id UUID,
    url TEXT,
    intelligence JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_messages_tickers ON messages USING GIN(tickers);
CREATE INDEX idx_messages_captured_at ON messages(captured_at DESC);
CREATE INDEX idx_messages_batch_id ON messages(batch_id);
CREATE INDEX idx_messages_platform ON messages(platform);
CREATE INDEX idx_messages_importance ON messages(importance_score);

-- -----------------------------------------------------
-- Message Batches Table
-- -----------------------------------------------------
DROP TABLE IF EXISTS message_batches CASCADE;
CREATE TABLE message_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_type TEXT NOT NULL CHECK (batch_type IN ('realtime', 'standard', 'archive')),
    message_count INTEGER NOT NULL DEFAULT 0,
    total_importance INTEGER DEFAULT 0,
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processed_at TIMESTAMPTZ,
    llm_tokens_used INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_batches_status ON message_batches(processing_status);
CREATE INDEX idx_batches_created ON message_batches(created_at DESC);

-- -----------------------------------------------------
-- Reports Table (Generated intelligence reports)
-- -----------------------------------------------------
DROP TABLE IF EXISTS reports CASCADE;
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id UUID REFERENCES message_batches(id),
    report_type TEXT NOT NULL CHECK (report_type IN ('alert', 'hourly', 'daily')),
    report_data JSONB NOT NULL,
    key_insights TEXT[],
    mentioned_tickers TEXT[],
    overall_sentiment TEXT CHECK (overall_sentiment IN ('bullish', 'bearish', 'neutral', 'mixed')),
    trading_signals JSONB,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    messages_analyzed INTEGER DEFAULT 0,
    processing_time_seconds DECIMAL(10,2),
    llm_tokens_used INTEGER,
    llm_model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reports_type ON reports(report_type);
CREATE INDEX idx_reports_created ON reports(created_at DESC);
CREATE INDEX idx_reports_tickers ON reports USING GIN(mentioned_tickers);
CREATE INDEX idx_reports_batch ON reports(batch_id);

-- -----------------------------------------------------
-- Report Subscriptions Table
-- -----------------------------------------------------
DROP TABLE IF EXISTS report_subscriptions CASCADE;
CREATE TABLE report_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    email TEXT,
    report_type TEXT NOT NULL CHECK (report_type IN ('alert', 'hourly', 'daily', 'all')),
    delivery_method TEXT NOT NULL CHECK (delivery_method IN ('email', 'webhook', 'dashboard')),
    webhook_url TEXT,
    configuration JSONB,
    is_active BOOLEAN DEFAULT true,
    last_delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_active ON report_subscriptions(is_active);
CREATE INDEX idx_subscriptions_type ON report_subscriptions(report_type);

-- -----------------------------------------------------
-- Ticker Statistics Table (Aggregated ticker data)
-- -----------------------------------------------------
DROP TABLE IF EXISTS ticker_stats CASCADE;
CREATE TABLE ticker_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    mention_count INTEGER DEFAULT 0,
    bullish_count INTEGER DEFAULT 0,
    bearish_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    average_importance DECIMAL(3,1),
    buy_signals INTEGER DEFAULT 0,
    sell_signals INTEGER DEFAULT 0,
    hold_signals INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker, date)
);

CREATE INDEX idx_ticker_stats_ticker ON ticker_stats(ticker);
CREATE INDEX idx_ticker_stats_date ON ticker_stats(date DESC);
CREATE INDEX idx_ticker_stats_mentions ON ticker_stats(mention_count DESC);

-- -----------------------------------------------------
-- Processing Jobs Table (Track background jobs)
-- -----------------------------------------------------
DROP TABLE IF EXISTS processing_jobs CASCADE;
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    payload JSONB,
    result JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_type ON processing_jobs(job_type);
CREATE INDEX idx_jobs_created ON processing_jobs(created_at DESC);

-- -----------------------------------------------------
-- System Metrics Table (Track system performance)
-- -----------------------------------------------------
DROP TABLE IF EXISTS system_metrics CASCADE;
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name TEXT NOT NULL,
    metric_value DECIMAL,
    metric_data JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metrics_name ON system_metrics(metric_name);
CREATE INDEX idx_metrics_timestamp ON system_metrics(timestamp DESC);

-- -----------------------------------------------------
-- Helper Functions
-- -----------------------------------------------------

-- Function to update ticker statistics
CREATE OR REPLACE FUNCTION update_ticker_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Update or insert ticker stats for each ticker in the message
    IF NEW.tickers IS NOT NULL AND array_length(NEW.tickers, 1) > 0 THEN
        FOR i IN 1..array_length(NEW.tickers, 1) LOOP
            INSERT INTO ticker_stats (
                ticker, 
                date, 
                mention_count,
                bullish_count,
                bearish_count,
                neutral_count,
                average_importance
            )
            VALUES (
                NEW.tickers[i],
                DATE(NEW.captured_at),
                1,
                CASE WHEN NEW.sentiment = 'bullish' THEN 1 ELSE 0 END,
                CASE WHEN NEW.sentiment = 'bearish' THEN 1 ELSE 0 END,
                CASE WHEN NEW.sentiment = 'neutral' THEN 1 ELSE 0 END,
                NEW.importance_score
            )
            ON CONFLICT (ticker, date) DO UPDATE
            SET 
                mention_count = ticker_stats.mention_count + 1,
                bullish_count = ticker_stats.bullish_count + CASE WHEN NEW.sentiment = 'bullish' THEN 1 ELSE 0 END,
                bearish_count = ticker_stats.bearish_count + CASE WHEN NEW.sentiment = 'bearish' THEN 1 ELSE 0 END,
                neutral_count = ticker_stats.neutral_count + CASE WHEN NEW.sentiment = 'neutral' THEN 1 ELSE 0 END,
                average_importance = (ticker_stats.average_importance * ticker_stats.mention_count + NEW.importance_score) / (ticker_stats.mention_count + 1),
                updated_at = NOW();
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic ticker stats update
CREATE TRIGGER update_ticker_stats_trigger
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION update_ticker_stats();

-- -----------------------------------------------------
-- Row Level Security (RLS) Policies
-- -----------------------------------------------------

-- Enable RLS on all tables
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticker_stats ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your auth setup)
-- For now, allowing all operations for development
CREATE POLICY "Allow all operations on messages" ON messages FOR ALL USING (true);
CREATE POLICY "Allow all operations on message_batches" ON message_batches FOR ALL USING (true);
CREATE POLICY "Allow all operations on reports" ON reports FOR ALL USING (true);
CREATE POLICY "Allow all operations on report_subscriptions" ON report_subscriptions FOR ALL USING (true);
CREATE POLICY "Allow all operations on ticker_stats" ON ticker_stats FOR ALL USING (true);

-- -----------------------------------------------------
-- Sample Data for Testing (Optional)
-- -----------------------------------------------------
-- Uncomment to insert sample data

/*
-- Sample message batch
INSERT INTO message_batches (batch_type, message_count, processing_status)
VALUES ('standard', 0, 'pending');

-- Sample subscription
INSERT INTO report_subscriptions (email, report_type, delivery_method)
VALUES ('user@example.com', 'hourly', 'email');
*/

-- -----------------------------------------------------
-- Indexes for Full Text Search (Optional)
-- -----------------------------------------------------
-- CREATE INDEX idx_messages_content_search ON messages USING GIN(to_tsvector('english', content));

-- -----------------------------------------------------
COMMENT ON TABLE messages IS 'Stores raw captured messages from Chrome Extension';
COMMENT ON TABLE message_batches IS 'Tracks batches of messages for processing';
COMMENT ON TABLE reports IS 'Stores AI-generated intelligence reports';
COMMENT ON TABLE report_subscriptions IS 'User subscriptions for report delivery';
COMMENT ON TABLE ticker_stats IS 'Aggregated statistics for each ticker';
COMMENT ON TABLE processing_jobs IS 'Background job tracking';
COMMENT ON TABLE system_metrics IS 'System performance metrics';

-- Success message
SELECT 'SignalScope database tables created successfully!' AS status;