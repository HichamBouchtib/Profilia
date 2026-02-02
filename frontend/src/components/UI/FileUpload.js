import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion } from 'framer-motion';
import { Upload, FileText, AlertCircle, CheckCircle, X, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';

const FileUpload = ({ 
  onFilesSelected, 
  maxFiles = 3,
  // maxSize is provided in BYTES (e.g., 16 * 1024 * 1024 for 16MB)
  maxSize = 20 * 1024 * 1024,
  acceptedTypes = ['.pdf']
}) => {
  const [files, setFiles] = useState([]);

  const onDrop = useCallback(async (acceptedFiles, rejectedFiles) => {
    // Handle rejected files (type/count). Size is validated manually below
    rejectedFiles.forEach((file) => {
      file.errors.forEach((error) => {
        if (error.code === 'file-invalid-type') {
          toast.error(`File ${file.file.name} has an invalid type.`);
        } else if (error.code === 'too-many-files') {
          toast.error(`Too many files. Maximum ${maxFiles} files allowed`);
        }
      });
    });

    // Handle accepted files with size validation
    if (acceptedFiles.length > 0) {
      const sizeCheckResults = acceptedFiles.map((file) => {
        try {
          // Size validation for all files
          if (file.size > maxSize) {
            toast.error(`File ${file.name} is too large. Maximum size is ${formatFileSize(maxSize)}.`);
            return { file, ok: false };
          }

          return { file, ok: true };
        } catch (e) {
          toast.error(`Failed to validate ${file.name}. Please try another file.`);
          return { file, ok: false };
        }
      });

      const validFiles = sizeCheckResults.filter(r => r.ok).map(r => r.file);

      if (validFiles.length === 0) {
        return;
      }

      const remainingSlots = Math.max(0, maxFiles - files.length);
      const filesToAdd = validFiles.slice(0, remainingSlots);

      if (filesToAdd.length === 0) {
        toast.error(`Cannot upload more than ${maxFiles} files`);
        return;
      }

      const newFiles = filesToAdd.map(file => ({
        file,
        id: Math.random().toString(36).substr(2, 9),
        status: 'ready'
      }));

      const updatedFiles = [...files, ...newFiles];
      setFiles(updatedFiles);
      onFilesSelected(updatedFiles.map(f => f.file));
      toast.success(`${filesToAdd.length} file(s) added successfully`);
    }
  }, [files, maxFiles, maxSize, acceptedTypes, onFilesSelected]);

  const buildAcceptOption = () => {
    const acceptOption = {};
    const lowered = acceptedTypes.map(t => t.toLowerCase());
    if (lowered.includes('.pdf')) {
      acceptOption['application/pdf'] = ['.pdf'];
    }
    return acceptOption;
  };

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: buildAcceptOption(),
    // Avoid double size validation here; we validate size manually above
    maxFiles: Math.max(0, maxFiles - files.length),
    multiple: true
  });

  const removeFile = (fileId) => {
    const fileToRemove = files.find(f => f.id === fileId);
    const updatedFiles = files.filter(f => f.id !== fileId);
    setFiles(updatedFiles);
    onFilesSelected(updatedFiles.map(f => f.file));
    
    if (fileToRemove) {
      toast.success(`"${fileToRemove.file.name}" removed successfully`);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getDropzoneStyles = () => {
    let baseStyles = 'border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200';
    
    if (files.length >= maxFiles) {
      return `${baseStyles} border-gray-200 bg-gray-50 cursor-not-allowed opacity-60`;
    } else if (isDragActive && !isDragReject) {
      return `${baseStyles} border-primary-400 bg-primary-50 cursor-pointer`;
    } else if (isDragReject) {
      return `${baseStyles} border-red-400 bg-red-50 cursor-pointer`;
    } else {
      return `${baseStyles} border-gray-300 hover:border-gray-400 hover:bg-gray-50 cursor-pointer`;
    }
  };

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <motion.div
        {...getRootProps()}
        className={getDropzoneStyles()}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center">
          <Upload className={`h-12 w-12 mb-4 ${
            isDragActive 
              ? isDragReject 
                ? 'text-red-400' 
                : 'text-primary-400'
              : 'text-gray-400'
          }`} />
          
          {files.length >= maxFiles ? (
            <>
              <p className="text-lg font-medium text-gray-500 mb-2">
                Maximum files reached
              </p>
              <p className="text-sm text-gray-400 mb-4">
                You have uploaded {files.length} of {maxFiles} allowed files
              </p>
              <p className="text-xs text-gray-400">
                Remove a file to add another one
              </p>
            </>
          ) : isDragActive ? (
            isDragReject ? (
              <p className="text-red-600 font-medium">Some files will be rejected</p>
            ) : (
              <p className="text-primary-600 font-medium">Drop the files here...</p>
            )
          ) : (
            <>
              <p className="text-lg font-medium text-gray-900 mb-2">
                Drop files here or click to browse
              </p>
              <p className="text-sm text-gray-500 mb-4">
                Upload your fiscal bundle documents ({files.length}/{maxFiles} files)
              </p>
              <div className="text-xs text-gray-400 space-y-1">
                <p>Accepted formats: .pdf</p>
                <p>Maximum {maxFiles} files</p>
              </div>
            </>
          )}
        </div>
      </motion.div>

      {/* File List */}
      {files.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-3"
        >
          <h4 className="text-sm font-medium text-gray-900">
            Selected Files ({files.length}/{maxFiles})
          </h4>
          
          <div className="space-y-2">
            {files.map((fileWrapper, index) => (
              <motion.div
                key={fileWrapper.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-primary-50 rounded-lg flex items-center justify-center">
                    <FileText className="h-5 w-5 text-primary-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {fileWrapper.file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(fileWrapper.file.size)}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <div className="flex items-center">
                    {fileWrapper.status === 'ready' ? (
                      <>
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-xs text-green-600 ml-1">Ready</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="h-4 w-4 text-red-500" />
                        <span className="text-xs text-red-600 ml-1" title={fileWrapper.error}>
                          Error
                        </span>
                      </>
                    )}
                  </div>
                  <button
                    onClick={() => removeFile(fileWrapper.id)}
                    className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                    title="Remove file"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      
    </div>
  );
};

export default FileUpload;
