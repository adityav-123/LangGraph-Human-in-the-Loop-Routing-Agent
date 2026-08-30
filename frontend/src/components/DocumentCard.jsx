const URGENCY_COLORS = {
  critical: "bg-red-100 text-red-800 border-red-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  normal: "bg-green-100 text-green-800 border-green-200",
  low: "bg-blue-100 text-blue-800 border-blue-200",
};

const DECISION_COLORS = {
  pending: "bg-orange-100 text-orange-800 border-orange-200",
  approved: "bg-green-100 text-green-800 border-green-200",
  rejected: "bg-red-100 text-red-800 border-red-200",
  rerouted: "bg-indigo-100 text-indigo-800 border-indigo-200",
};

const STATUS_COLORS = {
  uploaded: "bg-slate-100 text-slate-700 border-slate-200",
  classifying: "bg-amber-100 text-amber-800 border-amber-200",
  extracting_metadata: "bg-sky-100 text-sky-800 border-sky-200",
  routing: "bg-violet-100 text-violet-800 border-violet-200",
  awaiting_review: "bg-orange-100 text-orange-800 border-orange-200",
  post_approval: "bg-indigo-100 text-indigo-800 border-indigo-200",
  completed: "bg-emerald-100 text-emerald-800 border-emerald-200",
  failed: "bg-rose-100 text-rose-800 border-rose-200",
};

const STATUS_TEXT = {
  uploaded: "Upload received. Waiting to start processing.",
  classifying: "Classifying document type and urgency...",
  extracting_metadata: "Extracting structured metadata...",
  routing: "Assigning the right department and reviewer...",
  awaiting_review: "Ready for human review.",
  post_approval: "Applying post-review actions...",
  completed: "Workflow completed.",
  failed: "Workflow failed. Review the error details.",
};

function Badge({ label, type, isDecision = false }) {
  if (!label) return null;

  const colors = isDecision
    ? DECISION_COLORS[label]
    : type === "status"
      ? STATUS_COLORS[label]
      : URGENCY_COLORS[label];

  return (
    <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full border ${colors || "bg-gray-100 text-gray-800 border-gray-200"}`}>
      {label.replaceAll("_", " ")}
    </span>
  );
}

export function DocumentCard({ doc, onClick }) {
  const isPending = doc.processing_status === "awaiting_review" && doc.human_decision === "pending";
  const previewText = doc.error
    ? `Error: ${doc.error}`
    : doc.summary || STATUS_TEXT[doc.processing_status] || "Processing...";

  return (
    <div
      onClick={() => isPending && onClick(doc)}
      className={`bg-white border rounded-xl p-4 md:p-5 transition-shadow ${isPending ? "hover:shadow-md cursor-pointer border-gray-200" : "cursor-default border-gray-200 opacity-80"}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="text-sm font-semibold text-gray-900 truncate max-w-full">{doc.file_name}</span>
            <Badge label={doc.urgency} />
            <Badge label={doc.processing_status} type="status" />
            <Badge label={doc.human_decision} isDecision />
          </div>
          <p className={`text-sm line-clamp-2 ${doc.error ? "text-red-600 font-medium" : "text-gray-600"}`}>
            {previewText}
          </p>
        </div>
        <div className="text-right shrink-0 flex flex-col items-end gap-1">
          {doc.doc_type && (
            <div className="text-xs text-gray-500 capitalize">{doc.doc_type.replace("_", " ")}</div>
          )}
          {doc.assigned_department && (
            <div className="text-xs font-medium text-blue-600">to {doc.assigned_department}</div>
          )}
          {isPending && doc.doc_type && (
            <span className="text-xs text-blue-600 underline mt-1">Review</span>
          )}
        </div>
      </div>
    </div>
  );
}
