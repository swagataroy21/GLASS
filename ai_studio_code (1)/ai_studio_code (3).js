import React, { useState } from 'react';
import axios from 'axios';

const FileUpload = ({ onUploadSuccess, onError }) => {
    const [uploadMessage, setUploadMessage] = useState('');
    const [isUploading, setIsUploading] = useState(false);

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);
        setIsUploading(true);
        setUploadMessage('Uploading...');
        onError('');

        try {
            const response = await axios.post('http://localhost:8000/uploadfile/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                onUploadProgress: (progressEvent) => {
                    const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    setUploadMessage(`Uploading: ${percent}%`);
                }
            });
            setUploadMessage(response.data.message);
            onUploadSuccess(response.data.gl_accounts);
        } catch (err) {
            const errorMessage = err.response?.data?.detail || 'File upload failed.';
            setUploadMessage(errorMessage);
            onError(errorMessage);
            console.error(err);
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="file-upload-container">
            <input type="file" id="file-upload" onChange={handleFileUpload} disabled={isUploading} accept=".csv"/>
            {uploadMessage && <p className="upload-message">{uploadMessage}</p>}
        </div>
    );
};

export default FileUpload;