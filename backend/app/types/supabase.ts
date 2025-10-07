export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      chat_messages: {
        Row: {
          content: string
          created_at: string | null
          id: number
          role: string
          session_id: string | null
        }
        Insert: {
          content: string
          created_at?: string | null
          id?: number
          role: string
          session_id?: string | null
        }
        Update: {
          content?: string
          created_at?: string | null
          id?: number
          role?: string
          session_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "chat_messages_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "chat_sessions"
            referencedColumns: ["session_id"]
          },
        ]
      }
      chat_sessions: {
        Row: {
          context: Json | null
          created_at: string | null
          id: number
          last_activity: string | null
          session_id: string
          user_id: string | null
        }
        Insert: {
          context?: Json | null
          created_at?: string | null
          id?: number
          last_activity?: string | null
          session_id: string
          user_id?: string | null
        }
        Update: {
          context?: Json | null
          created_at?: string | null
          id?: number
          last_activity?: string | null
          session_id?: string
          user_id?: string | null
        }
        Relationships: []
      }
      semantic_chunks: {
        Row: {
          chunk_index: number
          created_at: string | null
          embedding: string | null
          end_position: number | null
          entities: Json | null
          entity_types: string[] | null
          id: string
          language: string | null
          metadata: Json | null
          sentence_count: number | null
          sentiment: string | null
          start_position: number | null
          text: string
          transcript_id: string
        }
        Insert: {
          chunk_index: number
          created_at?: string | null
          embedding?: string | null
          end_position?: number | null
          entities?: Json | null
          entity_types?: string[] | null
          id: string
          language?: string | null
          metadata?: Json | null
          sentence_count?: number | null
          sentiment?: string | null
          start_position?: number | null
          text: string
          transcript_id: string
        }
        Update: {
          chunk_index?: number
          created_at?: string | null
          embedding?: string | null
          end_position?: number | null
          entities?: Json | null
          entity_types?: string[] | null
          id?: string
          language?: string | null
          metadata?: Json | null
          sentence_count?: number | null
          sentiment?: string | null
          start_position?: number | null
          text?: string
          transcript_id?: string
        }
        Relationships: []
      }
      subscribers: {
        Row: {
          active: boolean | null
          created_at: string | null
          email: string
          id: number
          name: string | null
          preferences: Json | null
          updated_at: string | null
        }
        Insert: {
          active?: boolean | null
          created_at?: string | null
          email: string
          id?: number
          name?: string | null
          preferences?: Json | null
          updated_at?: string | null
        }
        Update: {
          active?: boolean | null
          created_at?: string | null
          email?: string
          id?: number
          name?: string | null
          preferences?: Json | null
          updated_at?: string | null
        }
        Relationships: []
      }
      trade_ideas: {
        Row: {
          created_at: string | null
          description: string
          id: number
          risk_level: string | null
          strategy: string | null
          tickers: string[] | null
          time_frame: string | null
          title: string
          transcript_id: string | null
        }
        Insert: {
          created_at?: string | null
          description: string
          id?: number
          risk_level?: string | null
          strategy?: string | null
          tickers?: string[] | null
          time_frame?: string | null
          title: string
          transcript_id?: string | null
        }
        Update: {
          created_at?: string | null
          description?: string
          id?: number
          risk_level?: string | null
          strategy?: string | null
          tickers?: string[] | null
          time_frame?: string | null
          title?: string
          transcript_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "trade_ideas_transcript_id_fkey"
            columns: ["transcript_id"]
            isOneToOne: false
            referencedRelation: "transcripts"
            referencedColumns: ["transcript_id"]
          },
        ]
      }
      trades: {
        Row: {
          action: string
          confidence: number | null
          created_at: string | null
          extracted_at: string | null
          id: number
          metadata: Json | null
          price: number | null
          quantity: number | null
          reasoning: string | null
          symbol: string
          timestamp_mentioned: string | null
          transcript_id: string | null
        }
        Insert: {
          action: string
          confidence?: number | null
          created_at?: string | null
          extracted_at?: string | null
          id?: number
          metadata?: Json | null
          price?: number | null
          quantity?: number | null
          reasoning?: string | null
          symbol: string
          timestamp_mentioned?: string | null
          transcript_id?: string | null
        }
        Update: {
          action?: string
          confidence?: number | null
          created_at?: string | null
          extracted_at?: string | null
          id?: number
          metadata?: Json | null
          price?: number | null
          quantity?: number | null
          reasoning?: string | null
          symbol?: string
          timestamp_mentioned?: string | null
          transcript_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "trades_transcript_id_fkey"
            columns: ["transcript_id"]
            isOneToOne: false
            referencedRelation: "transcripts"
            referencedColumns: ["transcript_id"]
          },
        ]
      }
      transcript_analyses: {
        Row: {
          analysis_type: string
          content: string
          created_at: string | null
          id: number
          transcript_id: string | null
        }
        Insert: {
          analysis_type: string
          content: string
          created_at?: string | null
          id?: number
          transcript_id?: string | null
        }
        Update: {
          analysis_type?: string
          content?: string
          created_at?: string | null
          id?: number
          transcript_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "transcript_analyses_transcript_id_fkey"
            columns: ["transcript_id"]
            isOneToOne: false
            referencedRelation: "transcripts"
            referencedColumns: ["transcript_id"]
          },
        ]
      }
      transcript_chunks: {
        Row: {
          chunk_index: number
          created_at: string | null
          embedding: string | null
          id: number
          is_first: boolean | null
          is_last: boolean | null
          metadata: Json | null
          position: number | null
          text: string
          transcript_id: string | null
        }
        Insert: {
          chunk_index: number
          created_at?: string | null
          embedding?: string | null
          id?: number
          is_first?: boolean | null
          is_last?: boolean | null
          metadata?: Json | null
          position?: number | null
          text: string
          transcript_id?: string | null
        }
        Update: {
          chunk_index?: number
          created_at?: string | null
          embedding?: string | null
          id?: number
          is_first?: boolean | null
          is_last?: boolean | null
          metadata?: Json | null
          position?: number | null
          text?: string
          transcript_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "transcript_chunks_transcript_id_fkey"
            columns: ["transcript_id"]
            isOneToOne: false
            referencedRelation: "transcripts"
            referencedColumns: ["transcript_id"]
          },
        ]
      }
      transcripts: {
        Row: {
          created_at: string | null
          date: string | null
          detailed_summary: string | null
          duration_seconds: number | null
          id: number
          meeting_id: string | null
          metadata: Json | null
          source: string | null
          summary: string | null
          title: string | null
          transcript_id: string
          updated_at: string | null
          word_count: number | null
        }
        Insert: {
          created_at?: string | null
          date?: string | null
          detailed_summary?: string | null
          duration_seconds?: number | null
          id?: number
          meeting_id?: string | null
          metadata?: Json | null
          source?: string | null
          summary?: string | null
          title?: string | null
          transcript_id: string
          updated_at?: string | null
          word_count?: number | null
        }
        Update: {
          created_at?: string | null
          date?: string | null
          detailed_summary?: string | null
          duration_seconds?: number | null
          id?: number
          meeting_id?: string | null
          metadata?: Json | null
          source?: string | null
          summary?: string | null
          title?: string | null
          transcript_id?: string
          updated_at?: string | null
          word_count?: number | null
        }
        Relationships: []
      }
      usage_ledger: {
        Row: {
          amount: number
          created_at: string | null
          id: number
          metadata: Json | null
          resource_type: string
          user_id: string
        }
        Insert: {
          amount: number
          created_at?: string | null
          id?: number
          metadata?: Json | null
          resource_type: string
          user_id: string
        }
        Update: {
          amount?: number
          created_at?: string | null
          id?: number
          metadata?: Json | null
          resource_type?: string
          user_id?: string
        }
        Relationships: []
      }
      user_feedback: {
        Row: {
          answer: string
          created_at: string | null
          feedback: string | null
          id: number
          question: string
          question_id: string
          rating: number | null
          transcript_id: string | null
        }
        Insert: {
          answer: string
          created_at?: string | null
          feedback?: string | null
          id?: number
          question: string
          question_id: string
          rating?: number | null
          transcript_id?: string | null
        }
        Update: {
          answer?: string
          created_at?: string | null
          feedback?: string | null
          id?: number
          question?: string
          question_id?: string
          rating?: number | null
          transcript_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "user_feedback_transcript_id_fkey"
            columns: ["transcript_id"]
            isOneToOne: false
            referencedRelation: "transcripts"
            referencedColumns: ["transcript_id"]
          },
        ]
      }
      user_profiles: {
        Row: {
          created_at: string | null
          email: string
          full_name: string | null
          id: string
          plan_limits: Json | null
          plan_type: string | null
          subscription_status: string | null
          updated_at: string | null
          user_id: string
        }
        Insert: {
          created_at?: string | null
          email: string
          full_name?: string | null
          id?: string
          plan_limits?: Json | null
          plan_type?: string | null
          subscription_status?: string | null
          updated_at?: string | null
          user_id: string
        }
        Update: {
          created_at?: string | null
          email?: string
          full_name?: string | null
          id?: string
          plan_limits?: Json | null
          plan_type?: string | null
          subscription_status?: string | null
          updated_at?: string | null
          user_id?: string
        }
        Relationships: []
      }
      youtube_videos: {
        Row: {
          auto_generated_captions: boolean | null
          category: string | null
          channel_id: string | null
          channel_name: string | null
          comment_count: number | null
          created_at: string | null
          id: number
          language: string | null
          like_count: number | null
          processed_by_user: string | null
          published_at: string | null
          tags: string[] | null
          thumbnail_url: string | null
          transcript_id: string | null
          updated_at: string | null
          video_id: string
          video_url: string
          view_count: number | null
        }
        Insert: {
          auto_generated_captions?: boolean | null
          category?: string | null
          channel_id?: string | null
          channel_name?: string | null
          comment_count?: number | null
          created_at?: string | null
          id?: number
          language?: string | null
          like_count?: number | null
          processed_by_user?: string | null
          published_at?: string | null
          tags?: string[] | null
          thumbnail_url?: string | null
          transcript_id?: string | null
          updated_at?: string | null
          video_id: string
          video_url: string
          view_count?: number | null
        }
        Update: {
          auto_generated_captions?: boolean | null
          category?: string | null
          channel_id?: string | null
          channel_name?: string | null
          comment_count?: number | null
          created_at?: string | null
          id?: number
          language?: string | null
          like_count?: number | null
          processed_by_user?: string | null
          published_at?: string | null
          tags?: string[] | null
          thumbnail_url?: string | null
          transcript_id?: string | null
          updated_at?: string | null
          video_id?: string
          video_url?: string
          view_count?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "youtube_videos_transcript_id_fkey"
            columns: ["transcript_id"]
            isOneToOne: false
            referencedRelation: "transcripts"
            referencedColumns: ["transcript_id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      binary_quantize: {
        Args: { "": string } | { "": unknown }
        Returns: unknown
      }
      check_extension_exists: {
        Args: { extension_name: string }
        Returns: Json
      }
      check_user_quota: {
        Args: { p_user_id: string; p_resource_type: string; p_amount: number }
        Returns: boolean
      }
      consume_user_quota: {
        Args: {
          p_user_id: string
          p_resource_type: string
          p_amount: number
          p_metadata?: Json
        }
        Returns: boolean
      }
      exec_sql: {
        Args: { sql: string }
        Returns: Json
      }
      get_user_quota_limits: {
        Args: { p_user_id: string }
        Returns: Json
      }
      get_user_quota_usage: {
        Args: { p_user_id: string }
        Returns: Json
      }
      halfvec_avg: {
        Args: { "": number[] }
        Returns: unknown
      }
      halfvec_out: {
        Args: { "": unknown }
        Returns: unknown
      }
      halfvec_send: {
        Args: { "": unknown }
        Returns: string
      }
      halfvec_typmod_in: {
        Args: { "": unknown[] }
        Returns: number
      }
      hnsw_bit_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      hnsw_halfvec_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      hnsw_sparsevec_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      hnswhandler: {
        Args: { "": unknown }
        Returns: unknown
      }
      ivfflat_bit_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      ivfflat_halfvec_support: {
        Args: { "": unknown }
        Returns: unknown
      }
      ivfflathandler: {
        Args: { "": unknown }
        Returns: unknown
      }
      l2_norm: {
        Args: { "": unknown } | { "": unknown }
        Returns: number
      }
      l2_normalize: {
        Args: { "": string } | { "": unknown } | { "": unknown }
        Returns: string
      }
      match_chunks: {
        Args: {
          query_embedding: string
          match_threshold?: number
          match_count?: number
        }
        Returns: {
          id: string
          transcript_id: string
          chunk_index: number
          text: string
          entities: Json
          language: string
          metadata: Json
          entity_types: string[]
          similarity: number
        }[]
      }
      match_chunks_by_entities: {
        Args: {
          query_embedding: string
          entity_types_filter: string[]
          match_threshold?: number
          match_count?: number
        }
        Returns: {
          id: string
          transcript_id: string
          chunk_index: number
          text: string
          entities: Json
          language: string
          metadata: Json
          entity_types: string[]
          similarity: number
        }[]
      }
      match_semantic_chunks: {
        Args: {
          query_embedding: string
          match_threshold?: number
          match_count?: number
        }
        Returns: {
          id: string
          transcript_id: string
          chunk_index: number
          text: string
          entities: Json
          language: string
          metadata: Json
          entity_types: string[]
          similarity: number
        }[]
      }
      match_transcript_semantic_chunks: {
        Args: {
          query_embedding: string
          transcript_id_param: string
          match_threshold?: number
          match_count?: number
        }
        Returns: {
          id: string
          transcript_id: string
          chunk_index: number
          text: string
          entities: Json
          language: string
          metadata: Json
          entity_types: string[]
          similarity: number
        }[]
      }
      sparsevec_out: {
        Args: { "": unknown }
        Returns: unknown
      }
      sparsevec_send: {
        Args: { "": unknown }
        Returns: string
      }
      sparsevec_typmod_in: {
        Args: { "": unknown[] }
        Returns: number
      }
      vector_avg: {
        Args: { "": number[] }
        Returns: string
      }
      vector_dims: {
        Args: { "": string } | { "": unknown }
        Returns: number
      }
      vector_norm: {
        Args: { "": string }
        Returns: number
      }
      vector_out: {
        Args: { "": string }
        Returns: unknown
      }
      vector_send: {
        Args: { "": string }
        Returns: string
      }
      vector_typmod_in: {
        Args: { "": unknown[] }
        Returns: number
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DefaultSchema = Database[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof Database },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof Database },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends { schema: keyof Database }
  ? Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const

// YouTube Extension specific types
export interface UserQuotaLimits {
  monthly_tokens: number
  daily_requests: number
  max_video_duration: number
  concurrent_jobs: number
  email_summaries: boolean
  priority_processing: boolean
}

export interface UserQuotaUsage {
  limits: UserQuotaLimits
  usage: {
    daily_requests: number
    monthly_tokens: number
  }
  remaining: {
    daily_requests: number
    monthly_tokens: number
  }
}

export interface YouTubeVideoMetadata {
  video_id: string
  channel_name?: string
  channel_id?: string
  video_url: string
  thumbnail_url?: string
  published_at?: string
  view_count?: number
  like_count?: number
  comment_count?: number
  category?: string
  tags?: string[]
  language?: string
  auto_generated_captions?: boolean
} 