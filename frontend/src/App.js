import React, { useState, useEffect } from 'react';

function App() {
  const [file1, setFile1] = useState(null);
  const [file2, setFile2] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [serverStatus, setServerStatus] = useState('checking');

  useEffect(() => {
    // Check if backend server is running
    fetch('http://localhost:8000/')
      .then(response => {
        if (response.ok) {
          setServerStatus('connected');
        } else {
          setServerStatus('error');
          setError('Backend server is not responding correctly');
        }
      })
      .catch(() => {
        setServerStatus('error');
        setError('Cannot connect to backend server. Please make sure it is running.');
      });
  }, []);

  const handleFile1Change = (event) => {
    setFile1(event.target.files[0]);
    setError('');
  };

  const handleFile2Change = (event) => {
    setFile2(event.target.files[0]);
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file1 || !file2) {
      setError('Please upload both files');
      return;
    }

    if (serverStatus !== 'connected') {
      setError('Cannot connect to server. Please try again later.');
      return;
    }

    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('file1', file1);
    formData.append('file2', file2);

    try {
      console.log('Sending request to backend...');
      const response = await fetch('http://localhost:8000/process-csv', {
        method: 'POST',
        body: formData,
      });

      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.text();
        console.error('Error response:', errorData);
        throw new Error(errorData || 'Server error occurred');
      }

      const blob = await response.blob();
      console.log('Received blob:', blob.size, 'bytes');
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'comparison_results.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error details:', error);
      setError(error.message || 'Error processing files. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 py-6 flex flex-col justify-center sm:py-12">
      <div className="relative py-3 sm:max-w-xl sm:mx-auto">
        <div className="relative px-4 py-10 bg-white shadow-lg sm:rounded-3xl sm:p-20">
          <div className="max-w-md mx-auto">
            <div className="divide-y divide-gray-200">
              <div className="py-8 text-base leading-6 space-y-4 text-gray-700 sm:text-lg sm:leading-7">
                <h1 className="text-2xl font-bold mb-8 text-center">File Comparison Tool</h1>
                {serverStatus === 'checking' && (
                  <div className="text-blue-500 text-sm text-center mb-4">Checking server connection...</div>
                )}
                {serverStatus === 'error' && (
                  <div className="text-red-500 text-sm text-center mb-4">Server connection error. Please make sure the backend is running.</div>
                )}
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      First File (HTML Content)
                    </label>
                    <input
                      type="file"
                      accept=".csv,.xlsx,.xls"
                      onChange={handleFile1Change}
                      className="mt-1 block w-full text-sm text-gray-500
                        file:mr-4 file:py-2 file:px-4
                        file:rounded-full file:border-0
                        file:text-sm file:font-semibold
                        file:bg-blue-50 file:text-blue-700
                        hover:file:bg-blue-100"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Second File (Product Descriptions)
                    </label>
                    <input
                      type="file"
                      accept=".csv,.xlsx,.xls"
                      onChange={handleFile2Change}
                      className="mt-1 block w-full text-sm text-gray-500
                        file:mr-4 file:py-2 file:px-4
                        file:rounded-full file:border-0
                        file:text-sm file:font-semibold
                        file:bg-blue-50 file:text-blue-700
                        hover:file:bg-blue-100"
                    />
                  </div>
                  {error && (
                    <div className="text-red-500 text-sm">{error}</div>
                  )}
                  <button
                    type="submit"
                    disabled={loading || !file1 || !file2 || serverStatus !== 'connected'}
                    className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white 
                      ${loading || !file1 || !file2 || serverStatus !== 'connected'
                        ? 'bg-gray-400 cursor-not-allowed' 
                        : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                      }`}
                  >
                    {loading ? 'Processing...' : 'Process Files'}
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App; 