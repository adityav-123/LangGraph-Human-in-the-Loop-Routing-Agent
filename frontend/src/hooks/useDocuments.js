import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../components/AuthProvider";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export function useDocuments(filter = "pending") {
  const { user, logout } = useAuth();
  const [docs, setDocs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDocs = useCallback(async () => {
    if (!user?.token) return;
    setLoading(true);
    try {
      const headers = { "Authorization": `Bearer ${user.token}` };
      const docsUrl = new URL(`${API}/documents`);
      docsUrl.searchParams.set("limit", "50");
      if (filter !== "all") {
        docsUrl.searchParams.set("decision", filter);
      }

      const [docsRes, statsRes] = await Promise.all([
        fetch(docsUrl.toString(), { headers }),
        fetch(`${API}/stats`, { headers }),
      ]);
      
      if (docsRes.status === 401) {
        logout();
        return;
      }
      
      setDocs(await docsRes.json());
      setStats(await statsRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [filter, user, logout]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  // Poll every 5s while any doc is still processing
  useEffect(() => {
    const hasProcessing = docs.some(d =>
      ["uploaded", "classifying", "extracting_metadata", "routing", "post_approval"].includes(d.processing_status)
    );
    if (!hasProcessing) return;
    const id = setInterval(fetchDocs, 5000);
    return () => clearInterval(id);
  }, [docs, fetchDocs]);

  return { docs, stats, loading, fetchDocs, API };
}
