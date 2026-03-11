export interface Inspection {
  id: string
  timestamp: string
  station_id: string
  part_id: string | null
  decision: 'pass' | 'fail' | 'uncertain'
  objects_found: number
  confidence: number
  total_time_ms: number | null
  thumbnail: string | null
}

export interface InspectionList {
  items: Inspection[]
  total: number
  limit: number
  offset: number
}

export interface Statistics {
  total_inspections: number
  passed: number
  failed: number
  uncertain: number
  pass_rate: number
  avg_inspection_time_ms: number
  defect_breakdown: Record<string, number>
}

export interface TrendData {
  labels: string[]
  total: number[]
  passed: number[]
  failed: number[]
  avg_time_ms?: number[]
}

export interface AppConfig {
  station_id: string
  api_port: number
  debug: boolean
  active_learning_enabled: boolean
  camera_type: string
  camera_index: number
  camera_width: number
  camera_height: number
  camera_fps: number
  detector_backbone: string
  confidence_threshold: number
  max_detections: number
  modbus_enabled: boolean
  modbus_host: string
  modbus_port: number
  mqtt_enabled: boolean
  mqtt_broker: string
  mqtt_port: number
  uncertainty_threshold_low?: number
  uncertainty_threshold_high?: number
  vlm_enabled: boolean
  vlm_backend: string
  vlm_local_model: string
  vlm_loaded: boolean
  anthropic_api_key?: string
  openai_api_key?: string
  groq_api_key?: string
  google_api_key?: string
  nvidia_nim_api_key?: string
  nvidia_nim_model?: string
  nvidia_nim_base_url?: string
}

export interface BatchJob {
  id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  input_dir: string
  file_pattern: string
  total_files: number
  processed_files: number
  failed_files: number
  created_at: string
}

export interface ActiveLearningStats {
  pending: number
  labeled: number
  trained: number
  total: number
}

export interface QueueItem {
  id: string
  image_path: string
  uncertainty_score: number
  status: string
}

export interface User {
  id: string
  username: string
  email: string
  roles: string[]
}

export interface StorageUsage {
  images_gb: number
  database_mb: number
  total_gb: number
}

export interface Alert {
  id: string
  severity: 'info' | 'warning' | 'error' | 'critical'
  title: string
  message: string
  timestamp: string
  acknowledged: boolean
}
