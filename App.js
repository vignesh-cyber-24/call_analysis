import React, { useState } from 'react';
import './App.css';

function App() {
    const [file, setFile] = useState(null);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);  // State to manage loading

    const handleFileChange = (event) => {
        setFile(event.target.files[0]);
    };

    const handleSubmit = async () => {
        setError(null); // Reset previous errors
        setResult(null); // Reset previous results
        setLoading(true); // Set loading to true when the analyze button is clicked

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://127.0.0.1:8000/analyze/', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'An unknown error occurred.');
            }

            const data = await response.json();
            setResult(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false); // Set loading to false after the request completes
        }
    };

    const handleAnalyzeDifferentAudio = () => {
        setFile(null);  // Reset the selected file
        setResult(null); // Clear the previous result
        setError(null);  // Clear any error messages
        setLoading(false); // Reset loading state
    };

    return (
        <div className="container">
            <div className="card">
                <h1>Audio Analyzer</h1>
                <input type="file" onChange={handleFileChange} />
                <button className="analyze-btn" onClick={handleSubmit} disabled={loading}>
                    {loading ? 'Analyzing Audio...' : 'Analyze'}
                </button>

                {error && <p className="error-message">{error}</p>}

                {result && (
                    <div className="result-box">
                        <h2>Transcription</h2>
                        <p>{result.transcription}</p>
                        <h2>Analysis</h2>
                        <p>{result.analysis}</p>
                    </div>
                )}

                {/* Analyze Different Audio Button */}
                {result && (
                    <button className="analyze-different-btn" onClick={handleAnalyzeDifferentAudio}>
                        Analyze Different Audio
                    </button>
                )}
            </div>
        </div>
    );
}

export default App;
