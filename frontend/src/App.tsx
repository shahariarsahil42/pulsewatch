import {
  useCallback,
  useEffect,
  useState,
} from "react";
import "./App.css";

type LogLevel =
  | "debug"
  | "info"
  | "warning"
  | "error"
  | "critical";

type LogEvent = {
  id: number;
  service_name: string;
  level: LogLevel;
  message: string;
  endpoint: string | null;
  response_time_ms: number | null;
  created_at: string;
};

type MetricsSummary = {
  total_events: number;
  error_count: number;
  warning_count: number;
  average_response_time_ms: number | null;
  monitored_services: number;
};

const API_URL = "http://127.0.0.1:8000";
const WEBSOCKET_URL = "ws://127.0.0.1:8000/ws/events";

const emptyMetrics: MetricsSummary = {
  total_events: 0,
  error_count: 0,
  warning_count: 0,
  average_response_time_ms: null,
  monitored_services: 0,
};

function App() {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [metrics, setMetrics] =
    useState<MetricsSummary>(emptyMetrics);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const loadMetrics = useCallback(async () => {
    const response = await fetch(
      `${API_URL}/metrics/summary`,
    );

    if (!response.ok) {
      throw new Error("Could not load monitoring metrics");
    }

    const data: MetricsSummary = await response.json();
    setMetrics(data);
  }, []);

  const loadDashboard = useCallback(async () => {
    try {
      const [eventsResponse, metricsResponse] =
        await Promise.all([
          fetch(`${API_URL}/events?limit=50`),
          fetch(`${API_URL}/metrics/summary`),
        ]);

      if (!eventsResponse.ok || !metricsResponse.ok) {
        throw new Error("Could not load dashboard data");
      }

      const eventsData: LogEvent[] =
        await eventsResponse.json();

      const metricsData: MetricsSummary =
        await metricsResponse.json();

      setErrorMessage("");
      setEvents(eventsData);
      setMetrics(metricsData);
    } catch {
      setErrorMessage(
        "PulseWatch API is offline. Start the backend server.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialLoadTimer = window.setTimeout(() => {
      void loadDashboard();
    }, 0);

    const websocket = new WebSocket(WEBSOCKET_URL);

    websocket.onopen = () => {
      setIsConnected(true);
    };

    websocket.onclose = () => {
      setIsConnected(false);
    };

    websocket.onerror = () => {
      setIsConnected(false);
    };

    websocket.onmessage = (message) => {
      const websocketMessage = JSON.parse(message.data);

      if (websocketMessage.type === "new_event") {
        const newEvent: LogEvent =
          websocketMessage.data;

        setEvents((currentEvents) => [
          newEvent,
          ...currentEvents,
        ].slice(0, 50));

        void loadMetrics();
      }
    };

    return () => {
      window.clearTimeout(initialLoadTimer);
      websocket.close();
    };
  }, [loadDashboard, loadMetrics]);

  function formatTime(timestamp: string) {
    return new Date(timestamp).toLocaleString(
      undefined,
      {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        second: "2-digit",
      },
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">P</div>

          <div>
            <h1>PulseWatch</h1>
            <p>Observability</p>
          </div>
        </div>

        <nav className="navigation">
          <button className="nav-item active">
            <span>◫</span>
            Overview
          </button>

          <button className="nav-item">
            <span>⌁</span>
            Live Events
          </button>

          <button className="nav-item">
            <span>⌁</span>
            Services
          </button>

          <button className="nav-item">
            <span>⚙</span>
            Settings
          </button>
        </nav>

        <div className="sidebar-footer">
          <div
            className={
              isConnected
                ? "connection-dot connected"
                : "connection-dot"
            }
          />

          <div>
            <strong>
              {isConnected
                ? "Live connection"
                : "Disconnected"}
            </strong>
            <span>WebSocket stream</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">
              MONITORING OVERVIEW
            </p>
            <h2>System health</h2>
          </div>

          <button
            className="refresh-button"
            onClick={() => void loadDashboard()}
          >
            Refresh data
          </button>
        </header>

        {errorMessage && (
          <div className="error-banner">
            <strong>Connection error</strong>
            <span>{errorMessage}</span>
          </div>
        )}

        <section className="metrics-grid">
          <article className="metric-card">
            <div className="metric-heading">
              <span>Total events</span>
              <div className="metric-icon purple">↗</div>
            </div>

            <strong>{metrics.total_events}</strong>
            <p>Events recorded by PulseWatch</p>
          </article>

          <article className="metric-card">
            <div className="metric-heading">
              <span>Errors</span>
              <div className="metric-icon red">!</div>
            </div>

            <strong>{metrics.error_count}</strong>
            <p>Events requiring attention</p>
          </article>

          <article className="metric-card">
            <div className="metric-heading">
              <span>Average response</span>
              <div className="metric-icon blue">◷</div>
            </div>

            <strong>
              {metrics.average_response_time_ms === null
                ? "—"
                : `${metrics.average_response_time_ms} ms`}
            </strong>
            <p>Across measured requests</p>
          </article>

          <article className="metric-card">
            <div className="metric-heading">
              <span>Services</span>
              <div className="metric-icon green">◆</div>
            </div>

            <strong>{metrics.monitored_services}</strong>
            <p>Applications reporting events</p>
          </article>
        </section>

        <section className="events-panel">
          <div className="panel-header">
            <div>
              <h3>Live event stream</h3>
              <p>
                The latest application activity,
                updated in real time
              </p>
            </div>

            <div className="live-badge">
              <span />
              LIVE
            </div>
          </div>

          <div className="table-wrapper">
            {isLoading ? (
              <div className="empty-state">
                Loading events...
              </div>
            ) : events.length === 0 ? (
              <div className="empty-state">
                <strong>No events recorded yet</strong>
                <span>
                  Send an event through the PulseWatch API
                  to see it here.
                </span>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Level</th>
                    <th>Service</th>
                    <th>Message</th>
                    <th>Endpoint</th>
                    <th>Response</th>
                    <th>Time</th>
                  </tr>
                </thead>

                <tbody>
                  {events.map((event) => (
                    <tr key={event.id}>
                      <td>
                        <span
                          className={`level-badge ${event.level}`}
                        >
                          {event.level}
                        </span>
                      </td>

                      <td className="service-name">
                        {event.service_name}
                      </td>

                      <td className="event-message">
                        {event.message}
                      </td>

                      <td>
                        <code>
                          {event.endpoint ?? "—"}
                        </code>
                      </td>

                      <td>
                        {event.response_time_ms === null
                          ? "—"
                          : `${event.response_time_ms} ms`}
                      </td>

                      <td className="event-time">
                        {formatTime(event.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;