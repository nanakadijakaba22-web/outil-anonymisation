'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, DatasetPreview, Dataset } from '@/lib/api';
import { formatFileSize } from '@/lib/utils';
import Stepper from '@/components/Stepper';
import ProgressBadge from '@/components/ProgressBadge';
import ProtectedRoute from '@/components/ProtectedRoute';
import Header from '@/components/Header';
import DataPreviewTable from '@/components/DataPreviewTable';

export default function Home() {
  const router = useRouter();
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Preview state
  const [showPreview, setShowPreview] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [uploadedDataset, setUploadedDataset] = useState<Dataset | null>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragging(true);
    } else if (e.type === 'dragleave') {
      setIsDragging(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files[0]) {
      handleFile(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      handleFile(files[0]);
    }
  };

  const handleFile = (selectedFile: File) => {
    // Validate file type
    if (!selectedFile.name.endsWith('.csv')) {
      setError('Seuls les fichiers CSV sont acceptés');
      return;
    }

    // Validate file size (1GB)
    const maxSize = 1 * 1024 * 1024 * 1024;
    if (selectedFile.size > maxSize) {
      setError('Le fichier est trop volumineux (max 1GB)');
      return;
    }

    setError(null);
    setFile(selectedFile);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const dataset = await api.uploadDataset(file);
      setUploadedDataset(dataset);

      // Load preview with timeout
      setLoadingPreview(true);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

      try {
        const previewData = await api.getDatasetPreview(dataset.id, 10, { signal: controller.signal });
        setPreview(previewData);
        setShowPreview(true);
      } catch (previewErr) {
        console.error('Error loading preview:', previewErr);

        if (previewErr instanceof Error && previewErr.name === 'AbortError') {
          setError('Délai d\'attente dépassé pour la prévisualisation. Vous pouvez continuer vers la détection.');
        } else {
          setError('Erreur lors du chargement de la prévisualisation. Vous pouvez continuer vers la détection.');
        }

        setShowPreview(true); // Allow user to continue even if preview fails
      } finally {
        clearTimeout(timeoutId);
        setLoadingPreview(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de l\'upload');
    } finally {
      setUploading(false);
    }
  };

  const handleContinueToDetection = () => {
    if (uploadedDataset) {
      router.push(`/detection/${uploadedDataset.id}`);
    }
  };

  const handleResetUpload = () => {
    setFile(null);
    setShowPreview(false);
    setPreview(null);
    setUploadedDataset(null);
    setError(null);
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <Header />
        {/* Progress Badge */}
        <ProgressBadge currentStep="upload" completedSteps={[]} />

      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Annoy
          </h1>
          <p className="text-xl text-gray-600 mb-2">
            Outil d'Anonymisation de Données
          </p>
          <p className="text-sm text-gray-500">
            Conforme à la Loi 25 du Québec
          </p>
        </div>

        {/* Stepper Navigation */}
        <Stepper currentStep="upload" completedSteps={[]} />

        {/* Main Card */}
        <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-xl p-8">
          {!showPreview ? (
            <>
              <div className="text-center mb-8">
                <h2 className="text-2xl font-semibold text-gray-800 mb-2">
                  Téléverser un fichier CSV
                </h2>
                <p className="text-gray-600">
                  Glissez-déposez votre fichier ou cliquez pour parcourir
                </p>
              </div>

          {/* Drop Zone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`
              relative border-2 border-dashed rounded-xl p-12 text-center transition-all
              ${
                isDragging
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              }
            `}
          >
            <input
              type="file"
              accept=".csv"
              onChange={handleFileInput}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              disabled={uploading}
            />

            <div className="pointer-events-none">
              {/* Upload Icon */}
              <svg
                className="mx-auto h-16 w-16 text-gray-400 mb-4"
                stroke="currentColor"
                fill="none"
                viewBox="0 0 48 48"
              >
                <path
                  d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>

              {!file ? (
                <>
                  <p className="text-gray-600 mb-2">
                    <span className="font-semibold text-blue-600">
                      Cliquez pour parcourir
                    </span>{' '}
                    ou glissez-déposez
                  </p>
                  <p className="text-sm text-gray-500">
                    Fichiers CSV uniquement (max 1GB)
                  </p>
                </>
              ) : (
                <div className="bg-gray-50 rounded-lg p-4 inline-block">
                  <p className="font-medium text-gray-800">{file.name}</p>
                  <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                    className="mt-2 text-sm text-red-600 hover:text-red-700"
                    disabled={uploading}
                  >
                    Supprimer
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Upload Button */}
          {file && !error && (
            <button
              onClick={handleUpload}
              disabled={uploading}
              className={`
                mt-6 w-full py-3 px-6 rounded-lg font-semibold text-white
                transition-all shadow-md
                ${
                  uploading
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 hover:shadow-lg'
                }
              `}
            >
              {uploading ? (
                <span className="flex items-center justify-center">
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Téléversement en cours...
                </span>
              ) : (
                'Téléverser et analyser'
              )}
            </button>
          )}

          {/* Features */}
          <div className="mt-8 pt-8 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              Ce qui se passera ensuite:
            </h3>
            <div className="grid gap-3">
              <div className="flex items-start">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-semibold mr-3">
                  1
                </span>
                <p className="text-sm text-gray-600">
                  <strong>Détection automatique</strong> des données sensibles (NAS, emails, etc.)
                </p>
              </div>
              <div className="flex items-start">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-semibold mr-3">
                  2
                </span>
                <p className="text-sm text-gray-600">
                  <strong>Configuration</strong> des techniques d'anonymisation
                </p>
              </div>
              <div className="flex items-start">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-semibold mr-3">
                  3
                </span>
                <p className="text-sm text-gray-600">
                  <strong>Évaluation</strong> de la conformité à la Loi 25
                </p>
              </div>
            </div>
          </div>
            </>
          ) : (
            <>
              {/* Preview View */}
              <div className="mb-8">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-semibold text-gray-800 mb-1">
                      Prévisualisation des données
                    </h2>
                    {uploadedDataset && (
                      <p className="text-sm text-gray-600">
                        Fichier: <span className="font-medium">{uploadedDataset.filename}</span>
                        {' '}({formatFileSize(uploadedDataset.file_size)})
                      </p>
                    )}
                  </div>
                  <button
                    onClick={handleResetUpload}
                    className="text-sm text-gray-600 hover:text-gray-800 flex items-center"
                  >
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    Nouveau fichier
                  </button>
                </div>

                {/* Preview Table or Loading */}
                {loadingPreview ? (
                  <DataPreviewTable preview={{} as DatasetPreview} isLoading={true} />
                ) : preview ? (
                  <DataPreviewTable preview={preview} />
                ) : (
                  <div className="text-center py-12 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <div className="max-w-md mx-auto">
                      <svg className="w-12 h-12 text-yellow-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <h3 className="text-lg font-medium text-gray-900 mb-2">
                        Prévisualisation indisponible
                      </h3>
                      <p className="text-sm text-gray-600 mb-4">
                        {error || 'Une erreur s\'est produite lors du chargement des données'}
                      </p>
                      <p className="text-sm text-gray-500">
                        Vous pouvez continuer vers la détection sans prévisualisation
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 pt-6 border-t border-gray-200">
                <button
                  onClick={handleResetUpload}
                  className="flex-1 py-3 px-6 rounded-lg font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 transition-all"
                >
                  Annuler
                </button>
                <button
                  onClick={handleContinueToDetection}
                  disabled={!uploadedDataset}
                  className="flex-1 py-3 px-6 rounded-lg font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg"
                >
                  Continuer vers la détection
                </button>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-sm text-gray-500">
          <p>
            Vos données sont traitées de manière sécurisée et confidentielle
          </p>
        </div>
      </div>
      </div>
    </ProtectedRoute>
  );
}
