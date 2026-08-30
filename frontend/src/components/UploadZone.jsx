import { useState } from "react";

export function UploadZone({ API, token, onUploadSuccess }) {
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`${API}/upload`, { 
        method: "POST", 
        headers: { "Authorization": `Bearer ${token}` },
        body: fd 
      });
      if (!res.ok) throw new Error(await res.text());
      onUploadSuccess();
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  return (
    <label className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${uploading ? 'bg-blue-400 cursor-not-allowed text-white' : 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer'}`}>
      {uploading ? "Uploading…" : "+ Upload document"}
      <input type="file" accept=".pdf,.docx,.txt,.png,.jpg" className="hidden" onChange={handleUpload} disabled={uploading} />
    </label>
  );
}
