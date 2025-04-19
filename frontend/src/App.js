import { useEffect, useState } from "react";
import axios from "axios";

const BACKEND = "http://localhost:8000";

function App() {
  const [nodes, setNodes] = useState(2);
  const [status, setStatus] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${BACKEND}/status`);
      setStatus(res.data);
      setError("");
    } catch {
      setError("Failed to fetch node status.");
    }
  };

  const startNodes = async () => {
    try {
      setLoading(true);
      setError("");
      await axios.post(`${BACKEND}/start/${nodes}`);
      await fetchStatus();
    } catch {
      setError("Failed to start nodes.");
    } finally {
      setLoading(false);
    }
  };

  const stopNodes = async () => {
    if (status.length === 0) return;
    try {
      setLoading(true);
      setError("");
      await axios.post(`${BACKEND}/stop`);
      await fetchStatus();
    } catch {
      setError("Failed to stop nodes.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000); // poll every 3 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: "2rem", fontFamily: "Arial, sans-serif", maxWidth: "600px", margin: "auto" }}>
      <h1 style={{ color: "#333" }}>DFL Mixnet Manager</h1>

      <div style={{ marginBottom: "1rem" }}>
        <label>
          <strong>Number of Nodes:</strong>{" "}
          <input
            type="number"
            min="1"
            value={nodes}
            onChange={(e) => setNodes(Number(e.target.value))}
            style={{ width: "60px", padding: "4px", marginLeft: "0.5rem" }}
            disabled={loading}
          />
        </label>
      </div>

      <div style={{ marginBottom: "1.5rem" }}>
        <button
          onClick={startNodes}
          disabled={loading}
          style={{ marginRight: "1rem", padding: "0.5rem 1rem" }}
        >
          Start
        </button>
        <button
          onClick={stopNodes}
          disabled={loading || status.length === 0}
          style={{ padding: "0.5rem 1rem" }}
        >
          Stop
        </button>
      </div>

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      <h2 style={{ marginTop: "2rem", color: "#333" }}>Node Status</h2>

      {status.length === 0 ? (
        <p>No containers running.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "0.5rem" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: "0.5rem" }}>Name</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: "0.5rem" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {status.map((node, idx) => (
              <tr key={idx}>
                <td style={{ padding: "0.5rem", borderBottom: "1px solid #eee" }}>{node.name}</td>
                <td style={{ padding: "0.5rem", borderBottom: "1px solid #eee" }}>{node.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default App;