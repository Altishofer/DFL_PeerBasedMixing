import { useEffect, useState } from "react";
import axios from "axios";

const BACKEND = "http://localhost:8000";

function App() {
  const [nodes, setNodes] = useState(5);
  const [status, setStatus] = useState([]);

  const fetchStatus = async () => {
    const res = await axios.get(`${BACKEND}/status`);
    setStatus(res.data);
  };

  const startNodes = async () => {
    await axios.post(`${BACKEND}/start/${nodes}`);
    fetchStatus();
  };

  const stopNodes = async () => {
    await axios.post(`${BACKEND}/stop`);
    fetchStatus();
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div style={{ padding: "2rem", fontFamily: "Arial" }}>
      <h1>DFL Mixnet Manager</h1>
      <label>
        Number of Nodes:{" "}
        <input
          type="number"
          value={nodes}
          onChange={(e) => setNodes(e.target.value)}
        />
      </label>
      <div style={{ marginTop: "1rem" }}>
        <button onClick={startNodes}>Start</button>{" "}
        <button onClick={stopNodes}>Stop</button>
      </div>

      <h2 style={{ marginTop: "2rem" }}>Node Status</h2>
      <pre>{JSON.stringify(status, null, 2)}</pre>
    </div>
  );
}

export default App;