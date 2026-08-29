const URGENCY_COLORS = {
  critical: "bg-red-100 text-red-800 border-red-200",
  high:     "bg-orange-100 text-orange-800 border-orange-200",
  normal:   "bg-green-100 text-green-800 border-green-200",
  low:      "bg-blue-100 text-blue-800 border-blue-200",
};

const DECISION_COLORS = {
  pending:  "bg-orange-100 text-orange-800 border-orange-200",
  approved: "bg-green-100 text-green-800 border-green-200",
  rejected: "bg-red-100 text-red-800 border-red-200",
  rerouted: "bg-indigo-100 text-indigo-800 border-indigo-200",
};

function Badge({ label, type, isDecision = false }) {
  if (!label) return null;
  const colors = isDecision ? DECISION_COLORS[label] : URGENCY_COLORS[label];
  return (
    <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full border ${colors || 'bg-gray-100 text-gray-800 border-gray-200'}`}>
      {label}
    </span>
  );
}

export function DocumentCard({ doc, onClick }) {
  const isPending = doc.human_decision === "pending";

  return (
    <div
      onClick={() => isPending && onClick(doc)}
      className={`bg-white border rounded-xl p-4 md:p-5 transition-shadow ${isPending ? 'hover:shadow-md cursor-pointer border-gray-200' : 'cursor-default border-gray-200 opacity-80'}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="text-sm font-semibold text-gray-900 truncate max-w-full">{doc.file_name}</span>
            <Badge label={doc.urgency} />
            <Badge label={doc.human_decision} isDecision />
          </div>
          <p className="text-sm text-gray-600 line-clamp-2">
            {doc.summary || (doc.doc_type ? "Metadata extracting…" : "Classifying…")}
          </p>
        </div>
        <div className="text-right shrink-0 flex flex-col items-end gap-1">
          {doc.doc_type && (
            <div className="text-xs text-gray-500 capitalize">{doc.doc_type.replace("_", " ")}</div>
          )}
          {doc.assigned_department && (
            <div className="text-xs font-medium text-blue-600">→ {doc.assigned_department}</div>
          )}
          {isPending && doc.doc_type && (
            <span className="text-xs text-blue-600 underline mt-1">Review →</span>
          )}
        </div>
      </div>
    </div>
  );
}
