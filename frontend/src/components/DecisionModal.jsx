import { useState } from "react";

export function DecisionModal({ doc, API, onClose, onDecision }) {
  const [notes, setNotes] = useState("");
  const [rerouteTo, setReroute] = useState("finance");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (action) => {
    if (action === "reject" && !notes.trim()) {
      setError("Rejection reason is required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const body = action === "reroute"
        ? { new_department: rerouteTo, reviewer_notes: notes }
        : { reviewer_notes: notes };

      const res = await fetch(`${API}/documents/${doc.document_id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Request failed");
      }
      onDecision();
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl"
      >
        <h3 className="text-lg font-semibold text-gray-900 mb-1">
          Review: {doc.file_name}
        </h3>
        <p className="text-sm text-gray-500 mb-4">
          {doc.summary || "No summary available."}
        </p>

        <div className="flex gap-2 flex-wrap mb-4">
          {doc.parties?.slice(0, 3).map(p => (
            <span key={p} className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">
              {p}
            </span>
          ))}
          {doc.key_dates?.slice(0, 2).map(d => (
            <span key={d} className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700">
              {d}
            </span>
          ))}
        </div>

        <textarea
          placeholder="Reviewer notes (required for rejection)"
          value={notes}
          onChange={e => { setNotes(e.target.value); setError(""); }}
          rows={3}
          className="w-full text-sm p-3 rounded-lg border border-gray-300 mb-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-y"
        />

        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 mb-1 block">Reroute to department</label>
          <select
            value={rerouteTo}
            onChange={e => setReroute(e.target.value)}
            className="w-full text-sm p-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 outline-none"
          >
            {["finance","legal","hr","medical","operations","compliance"].map(d => (
              <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
            ))}
          </select>
        </div>

        {error && <p className="text-sm text-red-600 mb-3 font-medium">{error}</p>}

        <div className="flex gap-3 mt-6">
          <button
            onClick={() => submit("approve")} disabled={loading}
            className="flex-1 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            {loading ? "…" : "Approve"}
          </button>
          <button
            onClick={() => submit("reject")} disabled={loading}
            className="flex-1 py-2.5 bg-white border-2 border-red-500 hover:bg-red-50 text-red-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            Reject
          </button>
          <button
            onClick={() => submit("reroute")} disabled={loading}
            className="flex-1 py-2.5 bg-white border-2 border-indigo-500 hover:bg-indigo-50 text-indigo-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            Reroute
          </button>
        </div>
      </div>
    </div>
  );
}
