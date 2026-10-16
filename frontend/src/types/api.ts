export type UserRole = 'farmer' | 'extension_agent' | 'admin';

export interface UserRecord {
  id: number | string;
  full_name?: string;
  name?: string;
  phone_number?: string;
  phone?: string;
  role: UserRole;
  is_active?: boolean;
  preferred_language?: 'en' | 'am';
  region?: string;
  woreda?: string;
  kebele?: string;
  created_at?: string;
}

export interface FarmerProfile {
  id?: number | string;
  user_id?: number | string;
  full_name?: string;
  preferred_language?: 'en' | 'am';
  region?: string;
  woreda?: string;
  kebele?: string;
  latitude?: number | null;
  longitude?: number | null;
  sms_opt_in?: boolean;
  updated_at?: string;
}

export interface ProfileResponseData {
  user: UserRecord;
  farmer_profile?: FarmerProfile | null;
}

export interface DiagnosisPrediction {
  class_name: string;
  confidence: number;
  model_name?: string;
  model_version?: string;
  prediction_time_ms?: number;
  inference_time?: number;
  probabilities?: Record<string, number>;
}

export interface DiagnosisExplainability {
  heatmap_url?: string;
  heatmap_filename?: string;
  overlay?: string;
  overlay_url?: string;
  overlay_filename?: string;
  method?: string;
  available?: boolean;
  message?: string;
}

export interface AdvisorySource {
  title?: string;
  organization?: string;
  source_type?: string;
  url?: string;
  year?: number | string;
  notes?: string;
}

export interface AdvisoryRecord {
  id?: number | string;
  advisory_id?: number | string;
  disease_class?: string;
  disease?: string;
  scientific_name?: string | null;
  confidence?: number | null;
  severity?: string;
  title?: string;
  heading?: string;
  description?: string;
  symptoms?: string[];
  causes?: string[];
  favorable_conditions?: string[];
  management?: string[];
  sources?: AdvisorySource[];
  validation?: Record<string, unknown>;
  disclaimer?: string;
  treatment?: string | string[];
  treatments?: string[];
  prevention?: string | string[];
  preventions?: string[];
  recommendations?: string | string[];
  advisory_text?: string;
  source?: string;
  language?: 'en' | 'am';
  created_at?: string;
}

export interface CompleteDiagnosisResponse {
  diagnosis: {
    prediction: DiagnosisPrediction;
    database_id?: number | string;
    explainability?: DiagnosisExplainability | null;
    heatmap_url?: string;
    overlay?: string;
    overlay_url?: string;
    image_url?: string;
    created_at?: string;
    outbreak?: {
      status?: string;
      queued?: boolean;
      diagnosis_id?: number | string;
      evaluated?: boolean;
      alert_triggered?: boolean;
      risk_level?: string;
      message?: string;
    } | null;
    outbreak_status?: {
      status?: string;
      evaluated?: boolean;
      alert_triggered?: boolean;
      risk_level?: string;
      message?: string;
    } | null;
  };
  advisory?: AdvisoryRecord | null;
  database?: {
    diagnosis_id?: number | string;
    advisory_id?: number | string;
  };
}

export interface DiagnosisHistoryItem {
  id: number | string;
  diagnosis_id?: number | string;
  user_id?: number | string;
  farmer_name?: string;
  farmer_phone?: string;
  disease_class?: string;
  class_name?: string;
  confidence: number;
  image_url?: string;
  heatmap_url?: string;
  model_name?: string;
  model_version?: string;
  language?: string;
  region?: string;
  woreda?: string;
  kebele?: string;
  latitude?: number | null;
  longitude?: number | null;
  advisory?: AdvisoryRecord | null;
  created_at?: string;
}

export interface WeatherData {
  city?: string;
  region?: string;
  woreda?: string;
  temperature?: number;
  temp?: number;
  feels_like?: number;
  humidity?: number;
  pressure?: number;
  wind_speed?: number;
  description?: string;
  condition?: string;
  rainfall_mm?: number;
  precipitation?: number;
  units?: string;
  timestamp?: string;
  advisory_note?: string;
  raw?: Record<string, unknown>;
}

export interface CropCalendarStage {
  id?: string | number;
  stage_name?: string;
  name?: string;
  phase?: string;
  months?: string | string[];
  start_month?: string;
  end_month?: string;
  description?: string;
  activities?: string[];
  disease_watch?: string[];
  recommendations?: string[];
}

export interface CropCalendarData {
  region?: string;
  woreda?: string;
  agro_ecology?: string;
  season?: string;
  language?: string;
  stages?: CropCalendarStage[];
  calendar?: CropCalendarStage[];
  recommendations?: string[];
  notes?: string;
}

export interface DiscussionReply {
  id: number | string;
  post_id?: number | string;
  author_id?: number | string;
  author_name?: string;
  author_role?: string;
  content: string;
  created_at?: string;
}

export interface DiscussionPost {
  id: number | string;
  title: string;
  content: string;
  post_type?: 'question' | 'advisory' | 'announcement' | 'alert' | string;
  priority?: 'low' | 'normal' | 'medium' | 'high' | 'urgent' | string;
  author_id?: number | string;
  author_name?: string;
  author_role?: string;
  author_verified?: boolean;
  region?: string;
  woreda?: string;
  kebele?: string;
  replies_count?: number;
  likes_count?: number;
  liked_by_current_user?: boolean;
  replies?: DiscussionReply[];
  image_path?: string | null;
  image_url?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface OutbreakAlert {
  id: number | string;
  alert_id?: number | string;
  disease_class: string;
  region: string;
  woreda?: string;
  kebele?: string;
  risk_level?: 'low' | 'medium' | 'high' | 'critical' | string;
  risk_score?: number;
  case_count?: number;
  status?: string;
  trigger_type?: 'manual' | 'automatic' | string;
  message?: string;
  description?: string;
  analysis_period_days?: number;
  created_at?: string;
}

export interface QueuedSyncItem {
  operation_id: string;
  operation_type: 'diagnosis';
  language: 'en' | 'am';
  explain: boolean;
  fileName: string;
  fileType: string;
  fileSize: number;
  imageDataUrl: string;
  createdAt: string;
  status: 'queued' | 'syncing' | 'succeeded' | 'failed';
  errorMessage?: string;
  serverResult?: CompleteDiagnosisResponse;
}
