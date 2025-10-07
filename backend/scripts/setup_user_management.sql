-- Enable Row Level Security (RLS) for all tables
ALTER TABLE public.transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transcript_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.key_points ENABLE ROW LEVEL SECURITY;

-- Create user_profiles table to store additional user information
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    company TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on user_profiles
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Create company table to store company information
CREATE TABLE IF NOT EXISTS public.companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    domain TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on companies
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;

-- Create company_users table to track which users belong to which company
CREATE TABLE IF NOT EXISTS public.company_users (
    company_id UUID REFERENCES public.companies(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'member',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (company_id, user_id)
);

-- Enable RLS on company_users
ALTER TABLE public.company_users ENABLE ROW LEVEL SECURITY;

-- Create transcript_access table to track which users/companies have access to which transcripts
CREATE TABLE IF NOT EXISTS public.transcript_access (
    transcript_id TEXT REFERENCES public.transcripts(transcript_id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    company_id UUID REFERENCES public.companies(id) ON DELETE CASCADE,
    access_level TEXT DEFAULT 'read',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (transcript_id, user_id)
);

-- Enable RLS on transcript_access
ALTER TABLE public.transcript_access ENABLE ROW LEVEL SECURITY;

-- Create function to handle new user registration
CREATE OR REPLACE FUNCTION public.handle_new_user_registration()
RETURNS TRIGGER AS $$
BEGIN
    -- Create user profile
    INSERT INTO public.user_profiles (id, first_name, last_name, company, role)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'first_name',
        NEW.raw_user_meta_data->>'last_name',
        NEW.raw_user_meta_data->>'company',
        COALESCE(NEW.raw_user_meta_data->>'role', 'user')
    );
    
    -- Try to find company by domain
    IF NEW.raw_user_meta_data->>'company' IS NOT NULL THEN
        -- If email domain matches company domain, add user to company
        DECLARE
            email_domain TEXT;
            company_id UUID;
        BEGIN
            email_domain := split_part(NEW.email, '@', 2);
            
            -- Check if company exists with this domain
            SELECT id INTO company_id FROM public.companies WHERE domain = email_domain LIMIT 1;
            
            -- If company exists, add user to company
            IF company_id IS NOT NULL THEN
                INSERT INTO public.company_users (company_id, user_id, role)
                VALUES (company_id, NEW.id, 'member');
            END IF;
        END;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger to handle new user registration
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_registration();

-- Create RLS policies for user_profiles
CREATE POLICY "Users can view their own profile"
ON public.user_profiles
FOR SELECT
USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
ON public.user_profiles
FOR UPDATE
USING (auth.uid() = id);

-- Create RLS policies for companies
CREATE POLICY "Company members can view their company"
ON public.companies
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.company_users
        WHERE company_id = id AND user_id = auth.uid()
    )
);

CREATE POLICY "Company admins can update their company"
ON public.companies
FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM public.company_users
        WHERE company_id = id AND user_id = auth.uid() AND role = 'admin'
    )
);

-- Create RLS policies for company_users
CREATE POLICY "Company members can view company members"
ON public.company_users
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.company_users cu
        WHERE cu.company_id = company_id AND cu.user_id = auth.uid()
    )
);

CREATE POLICY "Company admins can manage company members"
ON public.company_users
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM public.company_users cu
        WHERE cu.company_id = company_id AND cu.user_id = auth.uid() AND cu.role = 'admin'
    )
);

-- Create RLS policies for transcripts
CREATE POLICY "Users can view transcripts they have access to"
ON public.transcripts
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.transcript_access
        WHERE transcript_id = public.transcripts.transcript_id
        AND (user_id = auth.uid() OR company_id IN (
            SELECT company_id FROM public.company_users WHERE user_id = auth.uid()
        ))
    )
);

-- Create RLS policies for transcript_chunks
CREATE POLICY "Users can view transcript chunks they have access to"
ON public.transcript_chunks
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.transcript_access
        WHERE transcript_id = public.transcript_chunks.transcript_id
        AND (user_id = auth.uid() OR company_id IN (
            SELECT company_id FROM public.company_users WHERE user_id = auth.uid()
        ))
    )
);

-- Create RLS policies for key_points
CREATE POLICY "Users can view key points for transcripts they have access to"
ON public.key_points
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.transcript_access
        WHERE transcript_id = public.key_points.transcript_id
        AND (user_id = auth.uid() OR company_id IN (
            SELECT company_id FROM public.company_users WHERE user_id = auth.uid()
        ))
    )
);

-- Create RLS policies for transcript_access
CREATE POLICY "Users can view their transcript access"
ON public.transcript_access
FOR SELECT
USING (user_id = auth.uid() OR company_id IN (
    SELECT company_id FROM public.company_users WHERE user_id = auth.uid()
));

CREATE POLICY "Transcript owners can manage access"
ON public.transcript_access
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM public.transcript_access
        WHERE transcript_id = public.transcript_access.transcript_id
        AND user_id = auth.uid()
        AND access_level = 'owner'
    )
); 