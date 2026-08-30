import { useState } from "react";
import { useDocuments } from "../hooks/useDocuments";
import { UploadZone } from "../components/UploadZone";
import { DocumentCard } from "../components/DocumentCard";
import { DecisionModal } from "../components/DecisionModal";
import { useAuth } from "../components/AuthProvider";

export default function Queue() {
  const { user } = useAuth();
  const [filter, setFilter] = useState("pending");
  const [selected, setSelected] = useState(null);

  const { docs, stats, loading, fetchDocs, API } = useDocuments(filter);
  const filters = ["pending", "approved", "rejected", "all"];

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Document Queue</h1>
          {stats && (
            <p className="text-sm text-gray-500 mt-1">
              {stats.awaiting_review} awaiting review · {stats.processing} processing · {stats.failed} failed
            </p>
          )}
        </div>
        <UploadZone API={API} token={user?.token} onUploadSuccess={fetchDocs} />
      </div>

      {stats?.alerts?.length > 0 && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-900">Attention needed</p>
          <div className="mt-2 flex flex-col gap-2">
            {stats.alerts.map((alert) => (
              <div key={alert.id} className="rounded-lg border border-amber-100 bg-white/80 px-3 py-2 text-sm text-amber-900">
                <span className="font-medium">{alert.title}</span>
                <span className="text-amber-700"> · {alert.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-6">
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors border ${
              filter === f
                ? "bg-blue-50 border-blue-200 text-blue-700"
                : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f !== "all" && stats && ` (${stats[f] ?? 0})`}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="py-12 text-center text-gray-500 text-sm">Loading documents...</div>
      ) : docs.length === 0 ? (
        <div className="py-16 text-center border-2 border-dashed border-gray-200 rounded-xl bg-white text-gray-500 text-sm">
          No documents in this queue. Upload one to get started.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {docs.map((doc) => (
            <DocumentCard key={doc.document_id} doc={doc} onClick={setSelected} />
          ))}
        </div>
      )}

      {selected && (
        <DecisionModal
          doc={selected}
          API={API}
          token={user?.token}
          onClose={() => setSelected(null)}
          onDecision={fetchDocs}
        />
      )}
    </div>
  );
}
