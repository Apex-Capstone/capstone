import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { useAuthStore } from '@/store/authStore'
import { useEffect } from 'react'

const sections = [
  { id: 'overview', label: 'Overview' },
  { id: 'patient-model', label: 'PatientModel Plugins' },
  { id: 'evaluator', label: 'Evaluator Plugins' },
  { id: 'metrics', label: 'Metrics Plugins' },
  { id: 'registration', label: 'Plugin Registration' },
  { id: 'testing', label: 'Testing Plugins' },
  { id: 'best-practices', label: 'Best Practices' },
]

export const PluginDeveloperGuide = () => {
  const { user } = useAuthStore()

  useEffect(() => {
    // On mount, scroll to top
    window.scrollTo(0, 0)
  }, [])

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 md:ml-64 bg-gray-50">
          <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
            <nav className="mb-4 text-sm text-gray-500">
              Dashboard /{' '}
              {user?.role === 'admin' && (
                <>
                  <span className="text-gray-900">Developer Docs</span>
                </>
              )}
              {!user?.role && <span className="text-gray-900">Developer Docs</span>}
            </nav>

            <div className="flex flex-col gap-8 lg:flex-row">
              {/* Left sidebar navigation */}
              <aside className="lg:w-64 lg:flex-shrink-0">
                <div className="sticky top-24 hidden lg:block">
                  <h2 className="text-sm font-semibold text-gray-700 mb-3">
                    On this page
                  </h2>
                  <nav className="space-y-1 text-sm">
                    {sections.map((section) => (
                      <button
                        key={section.id}
                        onClick={() => {
                          const el = document.getElementById(section.id)
                          if (el) {
                            el.scrollIntoView({ behavior: 'smooth', block: 'start' })
                          }
                        }}
                        className="block w-full text-left rounded-md px-2 py-1 text-gray-700 hover:bg-emerald-50 hover:text-emerald-700"
                      >
                        {section.label}
                      </button>
                    ))}
                  </nav>
                </div>
              </aside>

              {/* Main content */}
              <article className="flex-1">
                <header className="mb-8">
                  <h1 className="text-3xl font-bold text-gray-900 mb-2" id="overview">
                    APEX Plugin Developer Guide
                  </h1>
                  <p className="text-gray-600 max-w-2xl">
                    This guide explains how to extend APEX by writing and registering your own
                    <span className="font-semibold"> PatientModel</span>,{' '}
                    <span className="font-semibold">Evaluator</span>, and{' '}
                    <span className="font-semibold">MetricsPlugin</span> implementations.
                  </p>
                </header>

                {/* 1. Introduction / Overview */}
                <section className="mb-6">
                  <h2 className="text-xl font-semibold mt-8 mb-3">Introduction</h2>
                  <p className="text-gray-700 mb-3">
                    APEX allows researchers and developers to extend the system by implementing plugins.
                    Plugins are configured via settings (for example, environment variables) and loaded
                    at runtime. You can swap the default patient model, evaluator, or metrics without
                    modifying core application code.
                  </p>
                </section>

                {/* 2. PatientModel Plugins */}
                <section className="mb-6" id="patient-model">
                  <h2 className="text-xl font-semibold mt-8 mb-3">PatientModel Plugins</h2>
                  <p className="text-gray-700 mb-3">
                    Implement the <span className="font-mono">PatientModel</span> protocol: an async
                    method <span className="font-mono">generate_response(state, clinician_input)</span>{' '}
                    that returns the simulated patient response as a string.
                  </p>

                  <h3 className="text-lg font-medium mt-6 mb-2">Example</h3>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-md text-sm overflow-x-auto mb-3">
                    <code>{`from typing import Any


class MyPatientModel:
    async def generate_response(self, state: Any, clinician_input: str) -> str:
        # Use state.case, state.session, state.conversation_history as needed.
        # Return the next patient utterance.
        return "I'm not sure how to feel about that."`}</code>
                  </pre>

                  <h3 className="text-lg font-medium mt-6 mb-2">Expected behavior</h3>
                  <ul className="list-disc pl-6 text-gray-700 space-y-1">
                    <li>
                      <span className="font-mono">state</span> is provided by the dialogue service and
                      typically has <span className="font-mono">case</span>,{' '}
                      <span className="font-mono">session</span>, and{' '}
                      <span className="font-mono">conversation_history</span>.
                    </li>
                    <li>
                      Your method should return a single string: the next patient turn. Keep responses
                      appropriate for the clinical context and, if relevant, the current SPIKES stage.
                    </li>
                  </ul>
                </section>

                {/* 3. Evaluator Plugins */}
                <section className="mb-6" id="evaluator">
                  <h2 className="text-xl font-semibold mt-8 mb-3">Evaluator Plugins</h2>
                  <p className="text-gray-700 mb-3">
                    Implement the <span className="font-mono">Evaluator</span> protocol: an async method{' '}
                    <span className="font-mono">evaluate(db, session_id)</span> that returns a{' '}
                    <span className="font-mono">FeedbackResponse</span>.
                  </p>

                  <h3 className="text-lg font-medium mt-6 mb-2">Example</h3>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-md text-sm overflow-x-auto mb-3">
                    <code>{`from sqlalchemy.orm import Session
from domain.models.sessions import FeedbackResponse


class MyEvaluator:
    async def evaluate(self, db: Session, session_id: int) -> FeedbackResponse:
        # Load session/turns from db, compute scores and text feedback.
        return FeedbackResponse(
            empathy_score=75.0,
            overall_score=80.0,
            strengths="Clear structure.",
            areas_for_improvement="More empathy phrases.",
            suggested_responses=[],
            timeline_events=[],
        )`}</code>
                  </pre>

                  <h3 className="text-lg font-medium mt-6 mb-2">Expected return type</h3>
                  <p className="text-gray-700">
                    <span className="font-mono">FeedbackResponse</span> (or a compatible type) with at
                    least empathy score, overall score, and optional strengths / areas for improvement,
                    suggested responses, and timeline events as defined in the domain model.
                  </p>
                </section>

                {/* 4. Metrics Plugins */}
                <section className="mb-6" id="metrics">
                  <h2 className="text-xl font-semibold mt-8 mb-3">Metrics Plugins</h2>
                  <p className="text-gray-700 mb-3">
                    Implement the <span className="font-mono">MetricsPlugin</span> protocol: a synchronous
                    method <span className="font-mono">compute(db, session_id)</span> that returns a
                    dictionary of metrics.
                  </p>

                  <h3 className="text-lg font-medium mt-6 mb-2">Example</h3>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-md text-sm overflow-x-auto mb-3">
                    <code>{`from typing import Any
from sqlalchemy.orm import Session


class MyMetricsPlugin:
    def compute(self, db: Session, session_id: int) -> dict[str, Any]:
        # Compute custom metrics from session/turns.
        return {
            "custom_metric_a": 42,
            "custom_metric_b": "value",
        }`}</code>
                  </pre>

                  <p className="text-gray-700">
                    The scoring / feedback pipeline calls all configured metrics plugins and merges or
                    stores their results. These metrics can be used for research export and analytics.
                  </p>
                </section>

                {/* 5. Plugin Registration */}
                <section className="mb-6" id="registration">
                  <h2 className="text-xl font-semibold mt-8 mb-3">Plugin Registration</h2>
                  <p className="text-gray-700 mb-3">
                    Plugins are registered by <span className="font-semibold">configuration</span>, not by
                    code registration. Set the following in your environment or settings:
                  </p>
                  <ul className="list-disc pl-6 text-gray-700 space-y-1 mb-3">
                    <li>
                      <span className="font-mono">patient_model_plugin=module.path:ClassName</span>
                    </li>
                    <li>
                      <span className="font-mono">evaluator_plugin=module.path:ClassName</span>
                    </li>
                    <li>
                      <span className="font-mono">metrics_plugins=module.path:ClassA module.path:ClassB</span>{' '}
                      (or the equivalent list in your config)
                    </li>
                  </ul>

                  <h3 className="text-lg font-medium mt-6 mb-2">Example plugin path</h3>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-md text-sm overflow-x-auto mb-3">
                    <code>{`plugins.patient_models.default_llm_patient:DefaultLLMPatientModel`}</code>
                  </pre>

                  <p className="text-gray-700">
                    The format is always <span className="font-mono">module.path:ClassName</span>. The
                    module must be importable (for example, under <span className="font-mono">backend/src</span>{' '}
                    or on <span className="font-mono">PYTHONPATH</span>), and the class must implement the
                    corresponding interface.
                  </p>
                </section>

                {/* 6. Testing Plugins */}
                <section className="mb-6" id="testing">
                  <h2 className="text-xl font-semibold mt-8 mb-3">Testing Plugins</h2>
                  <ul className="list-disc pl-6 text-gray-700 space-y-1 mb-3">
                    <li>
                      <span className="font-semibold">Location:</span> Add tests under{' '}
                      <span className="font-mono">backend/tests/plugins/</span>.
                    </li>
                    <li>
                      <span className="font-semibold">Patterns:</span> Reuse the patterns from existing plugin
                      tests: mock or override <span className="font-mono">get_patient_model</span>,{' '}
                      <span className="font-mono">get_evaluator</span>, or{' '}
                      <span className="font-mono">get_metrics_plugins</span> where needed, and clear{' '}
                      <span className="font-mono">lru_cache</span> on the plugin manager in tests that change
                      configuration so the new plugin is loaded.
                    </li>
                    <li>
                      <span className="font-semibold">Interfaces:</span> Prefer testing against the public
                      interface (for example, <span className="font-mono">generate_response</span>,{' '}
                      <span className="font-mono">evaluate</span>, <span className="font-mono">compute</span>)
                      so that refactors preserve behavior.
                    </li>
                  </ul>
                </section>

                {/* 7. Best Practices */}
                <section className="mb-6" id="best-practices">
                  <h2 className="text-xl font-semibold mt-8 mb-3">Best Practices</h2>
                  <ul className="list-disc pl-6 text-gray-700 space-y-2">
                    <li>
                      <span className="font-semibold">Keep plugins stateless where possible:</span> Rely on{' '}
                      <span className="font-mono">state</span>, <span className="font-mono">db</span>, and{' '}
                      <span className="font-mono">session_id</span> for input. Avoid global mutable state so
                      that plugins are safe under concurrency and caching.
                    </li>
                    <li>
                      <span className="font-semibold">Reuse services where possible:</span> Use existing
                      repositories and services (for example,{' '}
                      <span className="font-mono">ScoringService</span>, session / turn repos) inside your
                      plugin to stay consistent with the rest of the system and avoid duplicating logic.
                    </li>
                    <li>
                      <span className="font-semibold">Avoid modifying core services:</span> Extend behavior via
                      new plugins or new classes that implement the interfaces; do not change{' '}
                      <span className="font-mono">DialogueService</span> or{' '}
                      <span className="font-mono">ScoringService</span> internals to suit a single plugin.
                    </li>
                    <li>
                      <span className="font-semibold">Validate configuration early:</span> Use the same{' '}
                      <span className="font-mono">module.path:ClassName</span> format as the defaults. Invalid
                      paths cause errors at startup or first use, which is intentional so misconfiguration is
                      caught quickly.
                    </li>
                  </ul>
                </section>
              </article>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

