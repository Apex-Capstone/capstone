/**
 * Plugin registry types for patient models, evaluators, and metrics.
 *
 * @remarks
 * Shapes match the backend plugins listing endpoint grouped by plugin kind.
 */

/** Metadata for a single registered plugin. */
export interface PluginInfo {
  name: string
  version: string
}

/** Plugins available on the server, grouped by role. */
export interface PluginsResponse {
  patient_models: PluginInfo[]
  evaluators: PluginInfo[]
  metrics: PluginInfo[]
}
