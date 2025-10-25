import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Loader2, FileText, X } from 'lucide-react';
import { apiService } from '@/services/api';
import { useStore } from '@/store/useStore';
import toast from 'react-hot-toast';

export function UploadPanel() {
  const [files, setFiles] = useState<File[]>([]);
  const [projectName, setProjectName] = useState('');
  const [enableLLM, setEnableLLM] = useState(false);
  
  const { setProcessingStatus, setIsProcessing, setGraphData } = useStore();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    multiple: true,
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      toast.error('Please select at least one PDF file');
      return;
    }

    setIsProcessing(true);
    const loadingToast = toast.loading('Uploading PDFs...');

    try {
      // Start processing
      const status = await apiService.uploadPDFs(files, projectName, enableLLM);
      setProcessingStatus(status);

      // Poll for status
      const pollInterval = setInterval(async () => {
        try {
          const updatedStatus = await apiService.getStatus(status.job_id);
          setProcessingStatus(updatedStatus);

          if (updatedStatus.status === 'completed') {
            clearInterval(pollInterval);
            setIsProcessing(false);
            
            if (updatedStatus.result) {
              console.log('Graph data received:', updatedStatus.result);
              console.log('Nodes:', updatedStatus.result.nodes?.length);
              console.log('Edges:', updatedStatus.result.edges?.length);
              setGraphData(updatedStatus.result);
              toast.success('Knowledge graph generated successfully!', {
                id: loadingToast,
              });
            } else {
              console.error('No result in completed status:', updatedStatus);
              toast.error('No graph data received');
            }
          } else if (updatedStatus.status === 'failed') {
            clearInterval(pollInterval);
            setIsProcessing(false);
            toast.error(`Processing failed: ${updatedStatus.message}`, {
              id: loadingToast,
            });
          } else {
            toast.loading(
              `${updatedStatus.message} (${Math.round(updatedStatus.progress * 100)}%)`,
              { id: loadingToast }
            );
          }
        } catch (error) {
          clearInterval(pollInterval);
          setIsProcessing(false);
          toast.error('Failed to check processing status', { id: loadingToast });
        }
      }, 2000);
    } catch (error: any) {
      setIsProcessing(false);
      toast.error(error.response?.data?.detail || 'Upload failed', {
        id: loadingToast,
      });
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6">
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl shadow-2xl p-8 border border-gray-700">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">🧬</div>
          <h1 className="text-4xl font-bold text-white mb-2">
            Synapse Mapper
          </h1>
          <p className="text-gray-400">
            Transform biomedical PDFs into interactive knowledge graphs
          </p>
        </div>

        {/* Project Name */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Project Name (Optional)
          </label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="My Research Project"
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
            isDragActive
              ? 'border-primary-500 bg-primary-500/10'
              : 'border-gray-600 hover:border-gray-500 bg-gray-800/50'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          {isDragActive ? (
            <p className="text-white font-medium">Drop the PDFs here...</p>
          ) : (
            <>
              <p className="text-white font-medium mb-1">
                Click to upload or drag and drop
              </p>
              <p className="text-gray-400 text-sm">
                PDF files only • Multiple files supported
              </p>
            </>
          )}
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-6 space-y-2">
            <p className="text-sm font-medium text-gray-300">
              Selected Files ({files.length})
            </p>
            <div className="max-h-48 overflow-y-auto space-y-2">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between bg-gray-800 rounded-lg p-3"
                >
                  <div className="flex items-center space-x-3 flex-1 min-w-0">
                    <FileText className="w-5 h-5 text-primary-400 flex-shrink-0" />
                    <span className="text-sm text-white truncate">
                      {file.name}
                    </span>
                    <span className="text-xs text-gray-400 flex-shrink-0">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="ml-2 p-1 hover:bg-gray-700 rounded"
                  >
                    <X className="w-4 h-4 text-gray-400" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* LLM Option */}
        <div className="mt-6">
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={enableLLM}
              onChange={(e) => setEnableLLM(e.target.checked)}
              className="w-4 h-4 text-primary-600 bg-gray-800 border-gray-600 rounded focus:ring-primary-500"
            />
            <div>
              <span className="text-sm font-medium text-gray-300">
                Enable AI-Powered Extraction (Optional)
              </span>
              <p className="text-xs text-gray-500">
                Uses LLM for semantic relationship understanding (requires API key)
              </p>
            </div>
          </label>
        </div>

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={files.length === 0}
          className="w-full mt-8 py-3 px-6 bg-gradient-to-r from-primary-600 to-primary-500 text-white font-semibold rounded-lg shadow-lg hover:from-primary-700 hover:to-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center space-x-2"
        >
          {false ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Processing...</span>
            </>
          ) : (
            <>
              <Upload className="w-5 h-5" />
              <span>Generate Knowledge Graph</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

