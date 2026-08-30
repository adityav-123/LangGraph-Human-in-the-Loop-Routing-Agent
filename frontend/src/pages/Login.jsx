import { useState } from "react";
import { useAuth } from "../components/AuthProvider";

export function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(username, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="text-center mb-8">
          <div className="mx-auto w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
            <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Sign in to DocRouter</h2>
          <p className="mt-2 text-sm text-gray-600">Enterprise Document Triage Agent</p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              placeholder="e.g. admin, legal_reviewer"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>

          {error && (
            <div className="text-sm text-red-600 font-medium p-3 bg-red-50 rounded-lg border border-red-100">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="mt-6 border-t border-gray-100 pt-6">
          <p className="text-xs text-gray-500 font-medium mb-3 uppercase tracking-wider text-center">Demo Accounts</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-gray-50 p-2 rounded border border-gray-100 text-center cursor-pointer hover:bg-gray-100" onClick={() => setUsername("admin")}>
              <span className="font-semibold block text-gray-700">admin</span>
              <span className="text-gray-400">All access</span>
            </div>
            <div className="bg-gray-50 p-2 rounded border border-gray-100 text-center cursor-pointer hover:bg-gray-100" onClick={() => setUsername("legal_reviewer")}>
              <span className="font-semibold block text-gray-700">legal_reviewer</span>
              <span className="text-gray-400">Legal dept</span>
            </div>
            <div className="bg-gray-50 p-2 rounded border border-gray-100 text-center cursor-pointer hover:bg-gray-100" onClick={() => setUsername("hr_reviewer")}>
              <span className="font-semibold block text-gray-700">hr_reviewer</span>
              <span className="text-gray-400">HR dept</span>
            </div>
            <div className="bg-gray-50 p-2 rounded border border-gray-100 text-center cursor-pointer hover:bg-gray-100" onClick={() => setUsername("finance_reviewer")}>
              <span className="font-semibold block text-gray-700">finance_reviewer</span>
              <span className="text-gray-400">Finance dept</span>
            </div>
            <div className="bg-gray-50 p-2 rounded border border-gray-100 text-center cursor-pointer hover:bg-gray-100" onClick={() => setUsername("operations_reviewer")}>
              <span className="font-semibold block text-gray-700">operations_reviewer</span>
              <span className="text-gray-400">Operations dept</span>
            </div>
            <div className="bg-gray-50 p-2 rounded border border-gray-100 text-center cursor-pointer hover:bg-gray-100" onClick={() => setUsername("compliance_reviewer")}>
              <span className="font-semibold block text-gray-700">compliance_reviewer</span>
              <span className="text-gray-400">Compliance dept</span>
            </div>
            <div className="bg-gray-50 p-2 rounded border border-gray-100 text-center cursor-pointer hover:bg-gray-100" onClick={() => setUsername("medical_reviewer")}>
              <span className="font-semibold block text-gray-700">medical_reviewer</span>
              <span className="text-gray-400">Medical dept</span>
            </div>
          </div>
          <p className="text-[10px] text-gray-400 text-center mt-3">(Password is 'password123' for all)</p>
        </div>
      </div>
    </div>
  );
}
