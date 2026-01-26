'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { api } from '@/lib/api';
import type { DetectionReport, Dataset, ColumnClassification, BulkSensitivityUpdate } from '@/lib/api';
import {
  getSensitivityColor,
  formatSensitivityType,
  formatCategory,
  calculateColumnRiskScore,
  getRiskScoreColor,
} from '@/lib/utils';
import Stepper from '@/components/Stepper';
import ProgressBadge from '@/components/ProgressBadge';
import ProtectedRoute from '@/components/ProtectedRoute';
import Header from '@/components/Header';

type SensitivityType = 'direct_identifier' | 'quasi_identifier' | 'sensitive' | 'non_sensitive';
type Category = 'personal' | 'financial' | 'health' | 'insurance' | 'other';

interface EditableColumn extends ColumnClassification {
  isModified?: boolean;
}

export default function DetectionPage() {
  const router = useRouter();
  const params = useParams();
  const datasetId = params.id as string;

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [report, setReport] = useState<DetectionReport | null>(null);
  const [editedColumns, setEditedColumns] = useState<Record<string, EditableColumn>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [isAutoAnonymizing, setIsAutoAnonymizing] = useState(false);

  useEffect(() => {
    const runDetection = async () => {
      try {
        setLoading(true);
        setError(null);

        // Load dataset metadata
        const datasetData = await api.getDataset(datasetId);
        setDataset(datasetData);

        // Run detection
        const detectionReport = await api.detectSensitiveData(datasetId);
        setReport(detectionReport);
        setEditedColumns(detectionReport.columns);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur lors de la détection');
      } finally {
        setLoading(false);
      }
    };

    runDetection();
  }, [datasetId]);

  const handleSensitivityChange = (columnName: string, newSensitivity: SensitivityType) => {
    setEditedColumns(prev => ({
      ...prev,
      [columnName]: {
        ...prev[columnName],
        sensitivity_type: newSensitivity,
        isModified: true,
      }
    }));
    setHasChanges(true);
  };

  const handleCategoryChange = (columnName: string, newCategory: Category) => {
    setEditedColumns(prev => ({
      ...prev,
      [columnName]: {
        ...prev[columnName],
        category: newCategory,
        isModified: true,
      }
    }));
    setHasChanges(true);
  };

  const handleReset = () => {
    if (!report) return;
    setEditedColumns(report.columns);
    setHasChanges(false);
  };

  const handleSaveAndContinue = async () => {
    if (!hasChanges) {
      // No changes, proceed directly
      router.push(`/anonymization/${datasetId}`);
      return;
    }

    try {
      setSaving(true);
      setError(null);

      // Build bulk update request with only modified columns
      const updates: Record<string, { sensitivity_type: SensitivityType; category?: Category }> = {};

      Object.entries(editedColumns).forEach(([columnName, column]) => {
        if (column.isModified) {
          updates[columnName] = {
            sensitivity_type: column.sensitivity_type,
            category: column.category,
          };
        }
      });

      // Send bulk update if there are changes
      if (Object.keys(updates).length > 0) {
        await api.updateColumnsSensitivityBulk(datasetId, { updates });
      }

      // Navigate to anonymization
      router.push(`/anonymization/${datasetId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde');
      setSaving(false);
    }
  };

  const handleAutoAnonymize = async () => {
    setIsAutoAnonymizing(true);
    setError(null);
    try {
      const response = await api.autoAnonymizeDataset(datasetId);
      // Redirect to results page with anonymized dataset
      router.push(`/results/${response.anonymized_dataset_id}`);
    } catch (err) {
      console.error('Auto-anonymization failed:', err);
      setError(err instanceof Error ? err.message : 'Erreur lors de l\'anonymisation automatique');
      setIsAutoAnonymizing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mb-4"></div>
          <h2 className="text-2xl font-semibold text-gray-800">
            Analyse des données sensibles en cours...
          </h2>
          <p className="text-gray-600 mt-2">
            Classification des colonnes selon la Loi 25
          </p>
        </div>
      </div>
    );
  }

  if (error && !report) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="max-w-md bg-white rounded-lg shadow-xl p-8">
          <div className="text-red-600 mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2 text-center">
            Erreur de détection
          </h2>
          <p className="text-gray-600 text-center mb-4">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retour à l'accueil
          </button>
        </div>
      </div>
    );
  }

  if (!report || !dataset) {
    return null;
  }

  const columnEntries = Object.entries(editedColumns);

  // Recalculate summary based on edited columns
  const summary = {
    direct_identifier: 0,
    quasi_identifier: 0,
    sensitive: 0,
    non_sensitive: 0,
  };

  columnEntries.forEach(([_, col]) => {
    summary[col.sensitivity_type]++;
  });

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <Header />
        {/* Progress Badge */}
        <ProgressBadge currentStep="detection" completedSteps={['upload']} />

      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Résultats de la Détection
          </h1>
          <p className="text-lg text-gray-600">
            {dataset.filename}
          </p>
          <p className="text-sm text-gray-500">
            {dataset.row_count} lignes × {dataset.column_count} colonnes
          </p>
          {hasChanges && (
            <div className="mt-2 inline-flex items-center px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Modifications non sauvegardées
            </div>
          )}
        </div>

        {/* Stepper Navigation */}
        <Stepper
          currentStep="detection"
          datasetId={datasetId}
          completedSteps={['upload']}
        />

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Identifiants directs</p>
                <p className="text-3xl font-bold text-red-600">{summary.direct_identifier}</p>
              </div>
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Quasi-identifiants</p>
                <p className="text-3xl font-bold text-orange-600">{summary.quasi_identifier}</p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Données sensibles</p>
                <p className="text-3xl font-bold text-blue-600">{summary.sensitive}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Non-sensibles</p>
                <p className="text-3xl font-bold text-green-600">{summary.non_sensitive}</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Info Banner */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-8">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="text-sm font-semibold text-blue-900 mb-1">
                Validation manuelle requise
              </h3>
              <p className="text-sm text-blue-800">
                Vérifiez et ajustez la classification de chaque colonne ci-dessous.
                Vous pouvez modifier le type de sensibilité et la catégorie selon votre
                connaissance métier. Cette validation est importante pour la conformité à la Loi 25.
              </p>
            </div>
          </div>
        </div>

        {/* Editable Columns Table */}
        <div className="bg-white rounded-lg shadow-xl overflow-hidden mb-8">
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-800">
              Classification des Colonnes ({columnEntries.length})
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Modifiez les classifications si nécessaire
            </p>
          </div>

          {error && (
            <div className="px-6 py-3 bg-red-50 border-b border-red-200">
              <div className="flex items-center text-red-800">
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm font-medium">{error}</span>
              </div>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Colonne
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Type de sensibilité
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Catégorie
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Confiance
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Risque
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Justification
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {columnEntries.map(([columnName, column]) => {
                  const colors = getSensitivityColor(column.sensitivity_type);
                  return (
                    <tr
                      key={columnName}
                      className={`hover:bg-gray-50 ${column.isModified ? 'bg-yellow-50' : ''}`}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <span className="font-medium text-gray-900">{columnName}</span>
                          {column.isModified && (
                            <svg className="w-4 h-4 ml-2 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <select
                          value={column.sensitivity_type}
                          onChange={(e) => handleSensitivityChange(columnName, e.target.value as SensitivityType)}
                          className={`w-full px-3 py-2 rounded-lg border-2 ${colors.border} ${colors.bg} ${colors.text} font-medium focus:outline-none focus:ring-2 focus:ring-blue-500`}
                        >
                          <option value="direct_identifier">🔴 Identifiant direct</option>
                          <option value="quasi_identifier">🟠 Quasi-identifiant</option>
                          <option value="sensitive">🔵 Sensible</option>
                          <option value="non_sensitive">🟢 Non-sensible</option>
                        </select>
                      </td>
                      <td className="px-6 py-4">
                        <select
                          value={column.category}
                          onChange={(e) => handleCategoryChange(columnName, e.target.value as Category)}
                          className="w-full px-3 py-2 rounded-lg border border-gray-300 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="personal">Personnel</option>
                          <option value="financial">Financier</option>
                          <option value="health">Santé</option>
                          <option value="insurance">Assurance</option>
                          <option value="other">Autre</option>
                        </select>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <span className="text-lg font-bold text-gray-800">
                            {Math.round(column.confidence)}%
                          </span>
                          {column.isModified && (
                            <span className="ml-2 text-xs text-yellow-700 font-medium">
                              (modifié)
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {(() => {
                          const riskScore = calculateColumnRiskScore(column.sensitivity_type);
                          const riskColors = getRiskScoreColor(riskScore);
                          return (
                            <div className="flex items-center">
                              <span
                                className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${riskColors.bg} ${riskColors.text}`}
                                title="Risque de ré-identification basé sur le type de sensibilité"
                              >
                                {Math.round(riskScore)}%
                              </span>
                            </div>
                          );
                        })()}
                      </td>
                      <td className="px-6 py-4">
                        <p className="text-sm text-gray-700 max-w-md">
                          {column.justification}
                        </p>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 justify-center">
          <button
            onClick={() => router.push('/')}
            className="py-3 px-8 bg-gray-200 text-gray-800 rounded-lg font-semibold hover:bg-gray-300 transition-all"
          >
            Nouveau fichier
          </button>
          <button
            onClick={handleReset}
            disabled={!hasChanges}
            className={`py-3 px-8 rounded-lg font-semibold transition-all ${
              hasChanges
                ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200 border-2 border-yellow-300'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            Réinitialiser
          </button>
          <button
            onClick={handleSaveAndContinue}
            disabled={saving}
            className="py-3 px-8 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Sauvegarde...
              </span>
            ) : (
              hasChanges ? 'Sauvegarder et continuer →' : 'Continuer →'
            )}
          </button>
        </div>
      </div>
      </div>
    </ProtectedRoute>
  );
}
