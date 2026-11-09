export type UserRole = 'farmer' | 'extension_agent' | 'admin';

export interface FarmerNotificationPreferences {
  categories: Record<'crop_activity' | 'weather_alert' | 'soil_water_alert' | 'agricultural_advisory' | 'important_alerts', { in_app: boolean; sms: boolean; push: boolean }>;
  reminder_days_before: 0 | 1 | 2 | 3;
  quiet_hours: { enabled: boolean; start: string; end: string };
  timezone: string;
}

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
  notification_preferences?: FarmerNotificationPreferences;
  planting_date?: string | null;
  soil_type?: string | null;
  available_water_capacity_mm_per_m?: number | null;
  crop_growth_stage?: 'initial' | 'development' | 'mid_season' | 'late_season' | null;
  irrigation_status?: 'unknown' | 'rainfed' | 'irrigated' | null;
  last_irrigation_date?: string | null;
  last_irrigation_mm?: number | null;
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
  pesticide_recommendation?: string[];
  pesticide_safety?: string[];
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
  farmer_id?: number | string;
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
  location?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
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
  rainfall_period_hours?: number;
  precipitation?: number;
  units?: string;
  timestamp?: string;
  advisory_note?: string;
  raw?: Record<string, unknown>;
}

export interface WeatherForecastDay {
  date: string;
  weather_code: number | null;
  temperature_max: number | null;
  temperature_min: number | null;
  precipitation_mm: number | null;
  precipitation_probability: number | null;
  wind_speed_max: number | null;
  et0_mm?: number | null;
}

export interface SoilWaterEstimate {
  label: string;
  calculated_at: string;
  historical: { source?: string; data_type: string; start_date?: string | null; end_date?: string | null; rainfall_mm?: number | null; et0_mm?: number | null; etc_mm?: number | null; net_water_balance_mm?: number | null; latest_data_date?: string | null; stale: boolean };
  forecast: { source?: string; days: number; rainfall_mm?: number | null; et0_mm?: number | null; net_water_balance_mm?: number | null };
  crop_growth_stage?: string | null;
  soil_type?: string | null;
  irrigation_status?: string | null;
  root_zone?: { available_water_mm: number; total_available_water_mm: number; depletion_mm: number; unit: 'mm'; initialization: string } | null;
  weather_dryness_signal: 'net_deficit' | 'net_surplus' | 'unavailable';
  missing_inputs: string[];
  reliability: 'low' | 'moderate';
  assumptions: string[];
  recommendation: string;
  current_weather?: WeatherData | null;
  forecast_data?: FarmerWeatherForecastData['forecast'] | null;
  advisories?: AgriculturalAdvisories | null;
}

export interface AgriculturalAdvisorySource {
  key: string;
  url: string;
}

export interface AgriculturalAdvisorySupportingData {
  label_key: string;
  value: number | string;
  unit?: string;
  source_id: string;
}

export interface AgriculturalRecommendation {
  id: string;
  category: 'crop_stage' | 'weather' | 'soil_water';
  title_key: string;
  explanation_key: string;
  action_key: string;
  reason_key: string;
  stage_key: string;
  stage_basis: 'farmer_confirmed' | 'calendar_estimate';
  priority: 'routine' | 'medium' | 'high';
  priority_key: string;
  timing_key: string;
  source_ids: string[];
  sources: AgriculturalAdvisorySource[];
  reliability: 'low' | 'moderate';
  reliability_key: string;
  supporting_data: AgriculturalAdvisorySupportingData[];
}

export interface AgriculturalAdvisories {
  recommendations: AgriculturalRecommendation[];
  stage: {
    stage_key: string;
    basis: 'farmer_confirmed' | 'calendar_estimate';
    planting_date: string | null;
    calendar_stage_key: string;
    comparison: null | {
      confirmed_stage_key: string;
      calendar_stage_key: string;
      explanation_key: string;
    };
  };
  missing_data_keys: string[];
  disclaimer_key: string;
  method_key: string;
}

export interface FarmerWeatherForecastData {
  farmer_location: {
    region: string | null;
    woreda: string | null;
    kebele: string | null;
    latitude: number;
    longitude: number;
  };
  forecast: {
    provider: string;
    latitude: number | null;
    longitude: number | null;
    timezone: string | null;
    timezone_abbreviation: string | null;
    provider_timestamp: string | null;
    days: WeatherForecastDay[];
  };
}

export interface CropCalendarStage {
  stage: string;
  label: string;
  months: string[];
  activities?: string[];
}

export interface CropCalendarCurrentStage {
  stage: string;
  label: string;
  month: number;
  month_name: string;
  activities?: string[];
}

export interface CropCalendarReminder {
  activity_key: string;
  title: string;
  title_am: string;
  scheduled_date: string;
  stage: string;
  status: 'scheduled' | 'sent';
  is_read: boolean | null;
}

export interface CropCalendarData {
  crop: string;
  country: string;
  language: 'en' | 'am';
  location: {
    region: string;
    woreda: string | null;
    kebele: string | null;
  };
  season: string;
  regional_guidance: string;
  reference_date: string;
  current_stage: CropCalendarCurrentStage;
  calendar: CropCalendarStage[];
  upcoming_reminders?: CropCalendarReminder[];
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
