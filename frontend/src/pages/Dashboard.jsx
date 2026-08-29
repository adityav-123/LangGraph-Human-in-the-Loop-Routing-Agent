export function Dashboard({ children }) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
              </div>
              <span className="font-bold text-gray-900 text-lg tracking-tight">DocRouter</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium text-gray-500 bg-gray-100 px-3 py-1 rounded-full">v1.0 (Gemini)</span>
            </div>
          </div>
        </div>
      </nav>
      <main className="flex-1 max-w-5xl w-full mx-auto">
        {children}
      </main>
    </div>
  );
}
