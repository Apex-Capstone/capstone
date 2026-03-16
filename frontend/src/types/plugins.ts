export interface PluginInfo {
  name: string
  version: string
}

export interface PluginsResponse {
  patient_models: PluginInfo[]
  evaluators: PluginInfo[]
  metrics: PluginInfo[]
}
