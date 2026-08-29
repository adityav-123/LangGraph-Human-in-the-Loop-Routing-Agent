import { useState, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export function useDocuments(filter = "pending") {
  const [docs, setDocs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    try {
      const [docsRes, statsRes] = await Promise.all([
        fetch(`${API}/documents?decision=${filter}&limit=50`),
        fetch(`${API}/stats`),
      ]);
      setDocs(await docsRes.json());
      setStats(await statsRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  // Poll every 5s while any doc is still processing
  useEffect(() => {
    const hasProcessing = docs.some(d => !d.doc_type);
    if (!hasProcessing) return;
    const id = setInterval(fetchDocs, 5000);
    return () => clearInterval(id);
  }, [docs, fetchDocs]);

  return { docs, stats, loading, fetchDocs, API };
}
