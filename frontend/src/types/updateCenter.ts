export type UpdateResultStatus = "updated" | "up_to_date" | "not_configured" | "failed";

export interface UpdateCenterConfig {
  provider: string;
  auto_update_enabled: boolean;
  schedule_day: number;
  update_channel: string;
  manifest_url: string;
  app_manifest_url: string;
  proxy_url: string | null;
}

export interface UpdateCenterEvent {
  event: string;
  status: UpdateResultStatus | "scheduled";
  message: string;
  created_at: string;
}

export interface UpdateCenterStatus {
  config: UpdateCenterConfig;
  online_status: "not_configured" | "online" | "failed" | "offline";
  current_app_version: string;
  available_app_version: string | null;
  app_update_package_path: string | null;
  app_update_required: boolean;
  current_policy_version: string;
  current_policy_package_path: string | null;
  last_checked_at: string | null;
  last_successful_update_at: string | null;
  last_scheduled_check_at: string | null;
  last_scheduled_check_month: string | null;
  next_scheduled_check: string | null;
  last_error: string | null;
  events: UpdateCenterEvent[];
}

export interface UpdateCheckResult {
  status: UpdateResultStatus;
  message: string;
  current_policy_version: string;
  checked_at: string;
  manifest_version: string | null;
}

export interface ApplicationUpdateCheckResult {
  status: UpdateResultStatus;
  message: string;
  current_app_version: string;
  checked_at: string;
  available_app_version: string | null;
  update_package_path: string | null;
  mandatory: boolean;
}
