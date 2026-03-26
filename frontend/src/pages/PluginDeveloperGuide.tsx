/**
 * Long-form admin documentation for plugin architecture and registration.
 */
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { useAuthStore } from '@/store/authStore'
import { useEffect } from 'react'

/** In-page table of contents anchors. */
const sections = [
  { id: 'overview', label: 'Overview' },
  { id: 'architecture', label: 'Plugin Architecture' },
  { id: 'plugin-types', label: 'Plugin Types' },
  { id: 'patient-model', label: 'PatientModel Plugins' },
  { id: 'evaluator', label: 'Evaluator Plugins' },
  { id: 'metrics', label: 'Metrics Plugins' },
  { id: 'registration', label: 'Plugin Registration' },
  { id: 'testing', label: 'Testing Plugins' },
  { id: 'best-practices', label: 'Best Practices' },
]

/**
 * Scrollable developer guide with section anchors and prose blocks.
 *
 * @remarks
 * Scrolls to top on mount for predictable deep-link behavior.
 *
 * @returns Documentation layout
 */
export const PluginDeveloperGuide = () => {
  const { user } = useAuthStore()

  useEffect(() => {
    // On mount, scroll to top
    window.scrollTo(0, 0)
  }, [])

  return (
    <div className="h-screen flex flex-col">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 overflow-y-auto md:ml-64 bg-gray-50">
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
                        className="block w-full rounded-md px-2 py-1 text-left text-gray-700 hover:bg-apex-50 hover:text-apex-700"
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

                {/* 2. Plugin Architecture */}
                <section className="mb-6" id="architecture">
                  <h2 className="text-xl font-semibold mt-8 mb-3">Plugin Architecture</h2>
                  <p className="text-gray-700 mb-4">
                    APEX uses a pipeline architecture where each stage can be swapped via plugins.
                    The evaluation pipeline flows as follows:
                  </p>
                  <div className="rounded-lg border border-gray-200 bg-gray-900 p-5 text-sm font-mono text-gray-100 overflow-x-auto mb-4">
                    <div className="space-y-1">
                      <div className="text-indigo-300">Clinician Message</div>
                      <div className="text-gray-500">{'  →'} <span className="text-amber-300">Patient Model Plugin</span> <span className="text-gray-500">(generates patient response)</span></div>
                      <div className="text-gray-500">{'  →'} <span className="text-gray-300">Conversation</span> <span className="text-gray-500">(multi-turn dialogue)</span></div>
                      <div className="text-gray-500">{'  →'} <span className="text-emerald-300">Evaluator Plugin</span> <span className="text-gray-500">(scores communication, produces feedback)</span></div>
                      <div className="text-gray-500">{'  →'} <span className="text-gray-300">Feedback + Scores</span> <span className="text-gray-500">(FeedbackResponse)</span></div>
                      <div className="text-gray-500">{'  →'} <span className="text-purple-300">Metrics Plugins</span> <span className="text-gray-500">(compute research analytics)</span></div>
                      <div className="text-gray-500">{'  →'} <span className="text-gray-300">Analytics Dashboard</span></div>
                    </div>
                  </div>
                  <p className="text-gray-700">
                    Each plugin type implements a specific protocol (interface) and is configured via
                    environment variables using{' '}
                    <span className="font-mono text-sm">module.path:ClassName</span> format. Plugins are
                    resolved at session creation time and frozen on the session record, ensuring
                    reproducible results for research.
                  </p>
                </section>

                {/* 3. Plugin Types Overview */}
                <section className="mb-6" id="plugin-types">
                  <h2 className="text-xl font-semibold mt-8 mb-3">Plugin Types</h2>
                  <div className="space-y-4">
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                      <h3 className="font-semibold text-amber-900">Patient Model Plugin</h3>
                      <p className="text-sm text-amber-800 mt-1">
                        Generates simulated patient responses during training conversations. The plugin
                        receives the full conversation state (case context, session metadata, conversation
                        history) and returns the next patient utterance as a string.
                      </p>
                      <p className="text-xs text-amber-700 mt-2 font-mono">
                        Protocol: PatientModel.generate_response(state, clinician_input) → str
                      </p>
                    </div>
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                      <h3 className="font-semibold text-emerald-900">Evaluator Plugin</h3>
                      <p className="text-sm text-emerald-800 mt-1">
                        Scores clinician communication after a session ends and produces structured
                        feedback including numeric scores, text feedback, strengths, areas for
                        improvement, and optional framework-specific data (e.g. SPIKES coverage).
                      </p>
                      <p className="text-xs text-emerald-700 mt-2 font-mono">
                        Protocol: Evaluator.evaluate(db, session_id) → FeedbackResponse
                      </p>
                    </div>
                    <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
                      <h3 className="font-semibold text-purple-900">Metrics Plugin</h3>
                      <p className="text-sm text-purple-800 mt-1">
                        Computes additional analytics metrics for research dashboards and data exports.
                        Multiple metrics plugins can run in parallel, each producing a dictionary of
                        computed values from the session data.
                      </p>
                      <p className="text-xs text-purple-700 mt-2 font-mono">
                        Protocol: MetricsPlugin.compute(db, session_id) → dict[str, Any]
                      </p>
                    </div>
                  </div>
                </section>

                {/* 4. PatientModel Plugins */}
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
                  <p className="text-gray-700 mb-3">
                    <span className="font-mono">FeedbackResponse</span> (or a compatible type) with at
                    least empathy score, overall score, and optional strengths / areas for improvement,
                    suggested responses, and timeline events as defined in the domain model.
                  </p>

                  <h3 className="text-lg font-medium mt-6 mb-2">Complete evaluator example</h3>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-md text-sm overflow-x-auto mb-3">
                    <code>{`from sqlalchemy.orm import Session
from domain.models.sessions import FeedbackResponse
from repositories.session_repo import SessionRepository


class MyCustomEvaluator:
    """Custom evaluator with SPIKES + empathy scoring."""

    name = "my_custom_evaluator"
    version = "1.0.0"

    async def evaluate(self, db: Session, session_id: int) -> FeedbackResponse:
        repo = SessionRepository(db)
        session = repo.get(session_id)
        turns = repo.get_turns(session_id)

        # Implement your scoring logic here
        empathy_score = self._score_empathy(turns)
        spikes_score = self._score_spikes(turns)

        return FeedbackResponse(
            session_id=session_id,
            empathy_score=empathy_score,
            overall_score=(empathy_score + spikes_score) / 2,
            spikes_completion_score=spikes_score,
            strengths="Good use of open questions.",
            areas_for_improvement="Consider more reflective listening.",
            evaluator_meta={
                "name": self.name,
                "version": self.version,
                "framework": "SPIKES + Empathy",
            },
        )

    def _score_empathy(self, turns):
        # Your empathy scoring implementation
        return 75.0

    def _score_spikes(self, turns):
        # Your SPIKES scoring implementation
        return 80.0`}</code>
                  </pre>
                  <p className="text-gray-700 text-sm">
                    Include <span className="font-mono">evaluator_meta</span> in your response to provide
                    the UI with display context — the Feedback page will show the evaluator name and
                    framework to trainees.
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

